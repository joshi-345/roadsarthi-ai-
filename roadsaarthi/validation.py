"""Input validation for hazard reports.

Every function is pure: takes data in, returns (is_valid, error_message).
No UI, no database, no side effects.
"""

import io
import os

from PIL import Image

from roadsaarthi import config


def validate_category(category: str | None) -> tuple[bool, str]:
    """Validate that *category* is one of the allowed hazard types."""
    if not category:
        return False, "Please select a hazard category."
    if category not in config.HAZARD_CATEGORIES:
        return False, "Invalid hazard category selected."
    return True, ""


def validate_description(description: str | None) -> tuple[bool, str]:
    """Validate the free-text description.

    Leading/trailing whitespace is stripped before length checks.
    """
    if not description or not description.strip():
        return False, "Please provide a description of the hazard."

    trimmed = description.strip()
    if len(trimmed) < config.MIN_DESCRIPTION_LENGTH:
        return False, (
            f"Description must be at least "
            f"{config.MIN_DESCRIPTION_LENGTH} characters."
        )
    if len(trimmed) > config.MAX_DESCRIPTION_LENGTH:
        return False, (
            f"Description must not exceed "
            f"{config.MAX_DESCRIPTION_LENGTH} characters."
        )
    return True, ""


def validate_photo(
    file_name: str,
    file_type: str,
    file_size: int,
    file_data: bytes,
) -> tuple[bool, str]:
    """Validate an uploaded photo.

    Checks byte size, image content integrity and real format (detected by
    Pillow), extension, MIME type, and pixel dimensions.

    Parameters are plain Python types so the function is easy to test
    without mocking Streamlit's ``UploadedFile``.
    """
    # --- Byte size ---
    if file_size > config.MAX_PHOTO_SIZE_BYTES:
        return False, f"Photo must be under {config.MAX_PHOTO_SIZE_MB} MB."

    # --- Content integrity (verify) ---
    try:
        buf = io.BytesIO(file_data)
        img = Image.open(buf)
        img.verify()
    except Exception:
        return False, "The file does not appear to be a valid image."

    # --- Reopen after verify() to read format and dimensions ---
    # verify() leaves the image object unusable, so we must reopen.
    try:
        buf.seek(0)
        img = Image.open(buf)
        width, height = img.size
    except Exception:
        return False, "The file does not appear to be a valid image."

    # --- Real format (from file content, not extension/MIME) ---
    if img.format not in config.ALLOWED_PHOTO_FORMATS:
        return False, "Only JPEG and PNG photos are accepted."

    # --- Extension and MIME type ---
    # These are additional consistency checks; neither can override the
    # real format detected above.
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in config.ALLOWED_PHOTO_EXTENSIONS:
        return False, "Only JPEG and PNG photos are accepted."
    if file_type not in config.ALLOWED_PHOTO_TYPES:
        return False, "Only JPEG and PNG photos are accepted."

    if (
        width * height > config.MAX_PHOTO_PIXELS
        or width > config.MAX_PHOTO_DIMENSION
        or height > config.MAX_PHOTO_DIMENSION
    ):
        return False, (
            "Please use a smaller photo. Image dimensions must not exceed "
            f"{config.MAX_PHOTO_PIXELS:,} pixels total or "
            f"{config.MAX_PHOTO_DIMENSION}\u00d7{config.MAX_PHOTO_DIMENSION} pixels per side."
        )

    return True, ""


def validate_location(
    consent: bool,
    location_description: str | None,
    latitude: float | None,
    longitude: float | None,
) -> tuple[bool, str]:
    """Validate location fields.

    When *consent* is ``False`` the function returns success immediately —
    any location values supplied are irrelevant and will be discarded by
    the storage layer.
    """
    if not consent:
        return True, ""

    # --- Location description (required when consent is given) ---
    if not location_description or not location_description.strip():
        return False, "Please describe the location of the hazard."

    trimmed = location_description.strip()
    if len(trimmed) > config.MAX_LOCATION_DESCRIPTION_LENGTH:
        return False, (
            f"Location description must not exceed "
            f"{config.MAX_LOCATION_DESCRIPTION_LENGTH} characters."
        )

    # --- Lat / lon: both or neither ---
    has_lat = latitude is not None
    has_lon = longitude is not None

    if has_lat != has_lon:
        return False, (
            "Please provide both latitude and longitude, or leave both empty."
        )

    if has_lat and has_lon:
        if not (config.MIN_LATITUDE <= latitude <= config.MAX_LATITUDE):
            return False, "Latitude must be between \u221290 and +90."
        if not (config.MIN_LONGITUDE <= longitude <= config.MAX_LONGITUDE):
            return False, "Longitude must be between \u2212180 and +180."

    return True, ""
