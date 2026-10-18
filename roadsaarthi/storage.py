"""SQLite storage and photo persistence for hazard reports.

Responsibilities:
  - Create the ``reports`` table.
  - Insert a validated report row.
  - Save an uploaded photo to disk with EXIF stripped and a UUID filename.

All SQL uses parameterized queries.  The module never validates input —
that is the job of ``validation.py``.
"""

import io
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from PIL import Image, ImageOps

from roadsaarthi import config


# ── Database ────────────────────────────────────────────────────────────────


def init_db(db_path: str | None = None) -> None:
    """Create/upgrade reports; back up an existing DB before first upgrade."""
    db_path = db_path or config.DB_PATH
    existed = os.path.isfile(db_path) and os.path.getsize(db_path) > 0
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                category            TEXT    NOT NULL,
                description         TEXT    NOT NULL,
                photo_filename      TEXT,
                location_consent    INTEGER NOT NULL DEFAULT 0,
                location_description TEXT,
                latitude            REAL,
                longitude           REAL,
                status              TEXT    NOT NULL DEFAULT 'unverified',
                created_at          TEXT    NOT NULL
            )
            """
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(reports)")}
        additions = {
            "original_text": "TEXT",
            "summary": "TEXT",
            "assistant_used": "INTEGER",
            "ai_model": "TEXT",
        }
        missing = {name: kind for name, kind in additions.items() if name not in columns}
        if missing and existed:
            backup_path = f"{db_path}.pre_phase2.bak"
            if os.path.exists(backup_path):
                import time
                backup_path = f"{db_path}.pre_phase2.{time.time_ns()}.bak"
            backup = sqlite3.connect(backup_path)
            try:
                conn.backup(backup)
            finally:
                backup.close()
        for name, kind in missing.items():
            conn.execute(f"ALTER TABLE reports ADD COLUMN {name} {kind}")
        conn.execute(
            "UPDATE reports SET original_text = description "
            "WHERE original_text IS NULL"
        )
        conn.commit()
    finally:
        conn.close()


# ── Photo persistence ───────────────────────────────────────────────────────


def _save_photo(
    photo_data: bytes,
    original_extension: str,
    upload_dir: str | None = None,
) -> str:
    """Re-encode an image from pixel data and save it with a UUID filename.

    Re-encoding from raw pixel data (rather than copying the original
    bytes) strips **all** metadata, including EXIF and GPS tags.

    Returns the generated filename (not the full path).

    Raises ``ValueError`` if *original_extension* is not in the allowed set
    (defence-in-depth; validation should have already rejected it).
    """
    upload_dir = upload_dir or config.UPLOADS_DIR
    os.makedirs(upload_dir, exist_ok=True)

    ext = original_extension.lower()

    # Defence in depth — only allow known-safe extensions.
    if ext not in config.ALLOWED_PHOTO_EXTENSIONS:
        raise ValueError("Unsupported photo extension.")

    # Determine output format.
    if ext in (".jpg", ".jpeg"):
        fmt = "JPEG"
        out_ext = ".jpg"
    else:
        fmt = "PNG"
        out_ext = ".png"

    buf = io.BytesIO(photo_data)
    img = ImageOps.exif_transpose(Image.open(buf))
    img.thumbnail(
        (config.SAVED_PHOTO_MAX_DIMENSION, config.SAVED_PHOTO_MAX_DIMENSION),
        Image.Resampling.LANCZOS,
    )

    # Convert colour mode if needed (JPEG does not support alpha).
    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif fmt == "PNG" and img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGBA")

    # Re-encode from pixel data → new image with zero metadata.
    clean_img = Image.frombytes(img.mode, img.size, img.tobytes())

    filename = f"{uuid.uuid4().hex}{out_ext}"
    filepath = os.path.join(upload_dir, filename)
    clean_img.save(filepath, format=fmt)

    return filename


# ── Report persistence ──────────────────────────────────────────────────────


def save_report(
    category: str,
    description: str,
    photo_data: bytes | None = None,
    photo_extension: str | None = None,
    location_consent: bool = False,
    location_description: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    db_path: str | None = None,
    upload_dir: str | None = None,
    summary: str | None = None,
    assistant_used: bool = False,
    ai_model: str | None = None,
) -> int:
    """Persist a validated hazard report and return its integer ID.

    When *location_consent* is ``False``, any supplied location values are
    silently discarded so they are never stored.
    """
    db_path = db_path or config.DB_PATH
    upload_dir = upload_dir or config.UPLOADS_DIR

    # Save photo (if provided).
    photo_filename = None
    if photo_data and photo_extension:
        photo_filename = _save_photo(photo_data, photo_extension, upload_dir)

    # Discard location data when consent was not given.
    if not location_consent:
        location_description = None
        latitude = None
        longitude = None
    else:
        if location_description:
            location_description = location_description.strip()

    created_at = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO reports (
                category, description, photo_filename,
                location_consent, location_description, latitude, longitude,
                status, created_at, original_text, summary, assistant_used, ai_model
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category,
                description,
                photo_filename,
                1 if location_consent else 0,
                location_description,
                latitude,
                longitude,
                "unverified",
                created_at,
                description,
                summary,
                1 if assistant_used else 0,
                ai_model,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
