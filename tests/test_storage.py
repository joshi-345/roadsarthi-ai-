"""Unit tests for roadsaarthi.storage."""

import io
import os
import re
import sqlite3

import pytest
from PIL import Image

from roadsaarthi.storage import _save_photo, init_db, save_report


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_image_bytes(
    width: int = 100,
    height: int = 100,
    fmt: str = "JPEG",
    mode: str = "RGB",
) -> bytes:
    """Return valid image bytes for testing."""
    img = Image.new(mode, (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_jpeg_with_exif() -> bytes:
    """Return JPEG bytes that contain EXIF metadata."""
    img = Image.new("RGB", (100, 100), color="green")
    exif = img.getexif()
    exif[0x010F] = "TestCamera"  # EXIF tag: Make
    exif[0x0110] = "TestModel"  # EXIF tag: Model
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def db_path(tmp_path):
    """Create a temporary database and return its path."""
    path = str(tmp_path / "test.db")
    init_db(db_path=path)
    return path


@pytest.fixture()
def upload_dir(tmp_path):
    """Return a temporary upload directory path."""
    d = tmp_path / "uploads"
    d.mkdir()
    return str(d)


# ── init_db ─────────────────────────────────────────────────────────────────


class TestInitDb:
    def test_creates_reports_table(self, tmp_path):
        path = str(tmp_path / "fresh.db")
        init_db(db_path=path)

        conn = sqlite3.connect(path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent(self, db_path):
        """Calling init_db twice does not raise."""
        init_db(db_path=db_path)  # second call


# ── save_report ─────────────────────────────────────────────────────────────


class TestSaveReport:
    def test_minimal_report(self, db_path, upload_dir):
        """Category + description only, no photo, no location."""
        report_id = save_report(
            category="Pothole",
            description="Large pothole near the bus stop",
            db_path=db_path,
            upload_dir=upload_dir,
        )
        assert isinstance(report_id, int)
        assert report_id >= 1

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT category, description, photo_filename, status, created_at "
            "FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        conn.close()

        assert row[0] == "Pothole"
        assert row[1] == "Large pothole near the bus stop"
        assert row[2] is None  # no photo
        assert row[3] == "unverified"
        assert row[4]  # created_at is not empty

    def test_report_with_photo(self, db_path, upload_dir):
        photo_data = _make_image_bytes()
        report_id = save_report(
            category="Road Debris",
            description="Fallen tree branch blocking the left lane",
            photo_data=photo_data,
            photo_extension=".jpg",
            db_path=db_path,
            upload_dir=upload_dir,
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT photo_filename FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        conn.close()

        filename = row[0]
        assert filename is not None
        assert os.path.isfile(os.path.join(upload_dir, filename))

    def test_report_with_location(self, db_path, upload_dir):
        report_id = save_report(
            category="Pothole",
            description="Pothole near the railway crossing",
            location_consent=True,
            location_description="Near Bus Stand, Jalandhar",
            latitude=31.3260,
            longitude=75.5762,
            db_path=db_path,
            upload_dir=upload_dir,
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT location_consent, location_description, latitude, longitude "
            "FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        conn.close()

        assert row[0] == 1
        assert row[1] == "Near Bus Stand, Jalandhar"
        assert row[2] == pytest.approx(31.3260)
        assert row[3] == pytest.approx(75.5762)

    def test_full_report(self, db_path, upload_dir):
        """All fields populated."""
        photo_data = _make_image_bytes(fmt="PNG", mode="RGBA")
        report_id = save_report(
            category="Waterlogging / Flooding",
            description="Road completely submerged after heavy rain",
            photo_data=photo_data,
            photo_extension=".png",
            location_consent=True,
            location_description="GT Road underpass",
            latitude=30.9000,
            longitude=75.8573,
            db_path=db_path,
            upload_dir=upload_dir,
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        conn.close()

        # id, category, description, photo_filename,
        # location_consent, location_description, latitude, longitude,
        # status, created_at
        assert row[0] == report_id
        assert row[1] == "Waterlogging / Flooding"
        assert row[3] is not None  # photo saved
        assert row[4] == 1  # consent
        assert row[8] == "unverified"
        assert row[9]  # created_at


# ── EXIF stripping ──────────────────────────────────────────────────────────


class TestExifStripping:
    def test_source_has_exif(self):
        """Precondition: our helper actually produces EXIF data."""
        data = _make_jpeg_with_exif()
        img = Image.open(io.BytesIO(data))
        assert img.getexif().get(0x010F) == "TestCamera"

    def test_saved_photo_exif_stripped(self, tmp_path):
        data = _make_jpeg_with_exif()
        filename = _save_photo(data, ".jpg", upload_dir=str(tmp_path))

        saved_img = Image.open(tmp_path / filename)
        exif = saved_img.getexif()
        assert not exif, f"EXIF data should be empty but got: {dict(exif)}"

    def test_saved_photo_applies_exif_orientation(self, tmp_path):
        img = Image.new("RGB", (40, 20), color="green")
        exif = img.getexif()
        exif[274] = 6  # Rotate 90 degrees clockwise.
        buf = io.BytesIO()
        img.save(buf, format="JPEG", exif=exif.tobytes())

        filename = _save_photo(buf.getvalue(), ".jpg", upload_dir=str(tmp_path))

        with Image.open(tmp_path / filename) as saved_img:
            assert saved_img.size == (20, 40)


class TestSavedPhotoResizing:
    def test_large_photo_is_downscaled_to_2048_longest_side(self, tmp_path):
        data = _make_image_bytes(width=4000, height=3000)
        filename = _save_photo(data, ".jpg", upload_dir=str(tmp_path))

        with Image.open(tmp_path / filename) as saved_img:
            assert saved_img.size == (2048, 1536)

    def test_small_photo_is_not_enlarged(self, tmp_path):
        data = _make_image_bytes(width=100, height=80)
        filename = _save_photo(data, ".jpg", upload_dir=str(tmp_path))

        with Image.open(tmp_path / filename) as saved_img:
            assert saved_img.size == (100, 80)


# ── UUID filename ───────────────────────────────────────────────────────────


class TestUuidFilename:
    def test_filename_is_uuid_hex(self, tmp_path):
        data = _make_image_bytes()
        filename = _save_photo(data, ".jpg", upload_dir=str(tmp_path))

        stem, ext = os.path.splitext(filename)
        assert ext == ".jpg"
        assert re.match(r"^[0-9a-f]{32}$", stem), (
            f"Filename stem should be a 32-char hex UUID, got: {stem}"
        )

    def test_original_name_never_stored(self, db_path, upload_dir):
        """The DB stores the UUID filename, not the original."""
        data = _make_image_bytes()
        report_id = save_report(
            category="Pothole",
            description="Test that original name is not stored",
            photo_data=data,
            photo_extension=".jpg",
            db_path=db_path,
            upload_dir=upload_dir,
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT photo_filename FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        conn.close()

        filename = row[0]
        stem = os.path.splitext(filename)[0]
        assert re.match(r"^[0-9a-f]{32}$", stem)


# ── Security ────────────────────────────────────────────────────────────────


class TestSecurity:
    def test_sql_like_text_stored_safely(self, db_path, upload_dir):
        """SQL injection text in the description is stored verbatim."""
        malicious = "'; DROP TABLE reports; --"
        report_id = save_report(
            category="Pothole",
            description=malicious,
            db_path=db_path,
            upload_dir=upload_dir,
        )

        # The table still exists and the row is there.
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT description FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"
        ).fetchone()
        conn.close()

        assert row[0] == malicious
        assert tables is not None, "Table should still exist"

    def test_path_traversal_filename_safe(self, db_path, tmp_path):
        """The saved file always lands inside the upload directory."""
        upload_dir = str(tmp_path / "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        photo_data = _make_image_bytes()
        report_id = save_report(
            category="Pothole",
            description="Testing path traversal safety",
            photo_data=photo_data,
            photo_extension=".jpg",
            db_path=db_path,
            upload_dir=upload_dir,
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT photo_filename FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        conn.close()

        filename = row[0]
        saved_path = os.path.realpath(os.path.join(upload_dir, filename))
        expected_dir = os.path.realpath(upload_dir)

        # File is inside the intended directory.
        assert saved_path.startswith(expected_dir), (
            f"File {saved_path} escaped upload dir {expected_dir}"
        )
        assert os.path.isfile(saved_path)

        # No path separators in the filename itself.
        assert os.sep not in filename
        assert "/" not in filename

    def test_location_discarded_without_consent(self, db_path, upload_dir):
        """Location data is not stored when consent is False."""
        report_id = save_report(
            category="Pothole",
            description="Test that location is discarded",
            location_consent=False,
            location_description="Should be discarded",
            latitude=31.3260,
            longitude=75.5762,
            db_path=db_path,
            upload_dir=upload_dir,
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT location_consent, location_description, latitude, longitude "
            "FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        conn.close()

        assert row[0] == 0  # consent stored as false
        assert row[1] is None, "location_description should be NULL"
        assert row[2] is None, "latitude should be NULL"
        assert row[3] is None, "longitude should be NULL"
