"""Unit tests for roadsaarthi.validation."""

import io
import os

import pytest
from PIL import Image

from roadsaarthi import config
from roadsaarthi.validation import (
    validate_category,
    validate_description,
    validate_location,
    validate_photo,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_image_bytes(
    width: int = 100,
    height: int = 100,
    fmt: str = "JPEG",
    mode: str = "RGB",
) -> bytes:
    """Return valid image bytes for testing."""
    img = Image.new(mode, (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


# ── Category ────────────────────────────────────────────────────────────────


class TestValidateCategory:
    def test_valid_category(self):
        ok, msg = validate_category("Pothole")
        assert ok
        assert msg == ""

    def test_empty_string_rejected(self):
        ok, msg = validate_category("")
        assert not ok
        assert "select" in msg.lower()

    def test_none_rejected(self):
        ok, msg = validate_category(None)
        assert not ok

    def test_unknown_category_rejected(self):
        ok, msg = validate_category("Alien Invasion")
        assert not ok
        assert "invalid" in msg.lower()


# ── Description ─────────────────────────────────────────────────────────────


class TestValidateDescription:
    def test_valid_description(self):
        ok, msg = validate_description("A" * 15)
        assert ok

    def test_too_short(self):
        ok, msg = validate_description("Short")
        assert not ok
        assert str(config.MIN_DESCRIPTION_LENGTH) in msg

    def test_too_long(self):
        ok, msg = validate_description("A" * (config.MAX_DESCRIPTION_LENGTH + 1))
        assert not ok
        assert str(config.MAX_DESCRIPTION_LENGTH) in msg

    def test_whitespace_only(self):
        ok, msg = validate_description("   \t\n  ")
        assert not ok


# ── Photo ───────────────────────────────────────────────────────────────────


class TestValidatePhoto:
    def test_valid_jpeg(self):
        data = _make_image_bytes(fmt="JPEG")
        ok, msg = validate_photo("photo.jpg", "image/jpeg", len(data), data)
        assert ok

    def test_valid_png(self):
        data = _make_image_bytes(fmt="PNG")
        ok, msg = validate_photo("photo.png", "image/png", len(data), data)
        assert ok

    def test_disallowed_extension(self):
        data = _make_image_bytes(fmt="PNG")
        ok, msg = validate_photo("anim.gif", "image/gif", len(data), data)
        assert not ok
        assert "JPEG" in msg or "PNG" in msg

    def test_exceeds_max_size(self):
        # Create data that exceeds the limit (fake it with bytes, not a
        # real image — size check comes before content check).
        data = b"\x00" * (config.MAX_PHOTO_SIZE_BYTES + 1)
        ok, msg = validate_photo(
            "big.jpg", "image/jpeg", len(data), data
        )
        assert not ok
        assert str(config.MAX_PHOTO_SIZE_MB) in msg

    def test_spoofed_extension_rejected(self):
        """A .jpg file that is actually plain text is rejected."""
        data = b"This is definitely not an image file"
        ok, msg = validate_photo("fake.jpg", "image/jpeg", len(data), data)
        assert not ok
        assert "valid image" in msg.lower()

    def test_excessive_width_rejected(self):
        data = _make_image_bytes(
            width=config.MAX_PHOTO_DIMENSION + 1, height=1, fmt="PNG"
        )
        ok, msg = validate_photo("wide.png", "image/png", len(data), data)
        assert not ok
        assert "dimensions" in msg.lower()

    def test_excessive_height_rejected(self):
        data = _make_image_bytes(
            width=1, height=config.MAX_PHOTO_DIMENSION + 1, fmt="PNG"
        )
        ok, msg = validate_photo("tall.png", "image/png", len(data), data)
        assert not ok
        assert "dimensions" in msg.lower()

    def test_webp_renamed_to_jpg_rejected(self):
        """A real WebP file renamed to .jpg must be rejected.

        Extension and MIME type match the allowed set, but the real
        image format detected by Pillow is WEBP, which is not allowed.
        """
        data = _make_image_bytes(fmt="WEBP")
        ok, msg = validate_photo("photo.jpg", "image/jpeg", len(data), data)
        assert not ok
        assert "JPEG" in msg or "PNG" in msg

    def test_webp_native_extension_rejected(self):
        """A WebP file with its real .webp extension is rejected."""
        data = _make_image_bytes(fmt="WEBP")
        ok, msg = validate_photo("photo.webp", "image/webp", len(data), data)
        assert not ok


# ── Location ────────────────────────────────────────────────────────────────


class TestValidateLocation:
    def test_valid_with_consent_and_coords(self):
        ok, msg = validate_location(
            consent=True,
            location_description="Near Bus Stand, Jalandhar",
            latitude=31.3260,
            longitude=75.5762,
        )
        assert ok

    def test_valid_with_consent_description_only(self):
        """Lat/lon are optional — description alone is enough."""
        ok, msg = validate_location(
            consent=True,
            location_description="Near Bus Stand, Jalandhar",
            latitude=None,
            longitude=None,
        )
        assert ok

    def test_latitude_out_of_range(self):
        ok, msg = validate_location(
            consent=True,
            location_description="Somewhere",
            latitude=91.0,
            longitude=75.0,
        )
        assert not ok
        assert "latitude" in msg.lower() or "90" in msg

    def test_longitude_out_of_range(self):
        ok, msg = validate_location(
            consent=True,
            location_description="Somewhere",
            latitude=31.0,
            longitude=181.0,
        )
        assert not ok
        assert "longitude" in msg.lower() or "180" in msg

    def test_only_latitude_rejected(self):
        ok, msg = validate_location(
            consent=True,
            location_description="Somewhere",
            latitude=31.0,
            longitude=None,
        )
        assert not ok
        assert "both" in msg.lower()

    def test_consent_false_ignores_all_fields(self):
        """When consent is False, any supplied values are irrelevant."""
        ok, msg = validate_location(
            consent=False,
            location_description=None,
            latitude=999.0,   # invalid, but should be ignored
            longitude=-999.0,  # invalid, but should be ignored
        )
        assert ok
        assert msg == ""

    def test_description_too_long(self):
        ok, msg = validate_location(
            consent=True,
            location_description="A" * (config.MAX_LOCATION_DESCRIPTION_LENGTH + 1),
            latitude=None,
            longitude=None,
        )
        assert not ok
        assert str(config.MAX_LOCATION_DESCRIPTION_LENGTH) in msg

    def test_missing_description_with_consent(self):
        ok, msg = validate_location(
            consent=True,
            location_description="",
            latitude=31.0,
            longitude=75.0,
        )
        assert not ok
        assert "describe" in msg.lower() or "location" in msg.lower()
