"""Application constants for RoadSaarthi AI.

All magic numbers, allowed values and paths live here.
Imported by validation, storage and the Streamlit UI.
"""

import os

# ---------------------------------------------------------------------------
# Project root (one level above this file's directory)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Hazard categories
# ---------------------------------------------------------------------------
HAZARD_CATEGORIES: tuple[str, ...] = (
    "Pothole",
    "Broken Guardrail",
    "Missing / Damaged Sign",
    "Waterlogging / Flooding",
    "Road Debris",
    "Unmarked Speed Bump",
    "Damaged Road Surface",
    "Other",
)

# ---------------------------------------------------------------------------
# Description limits
# ---------------------------------------------------------------------------
MIN_DESCRIPTION_LENGTH: int = 10
MAX_DESCRIPTION_LENGTH: int = 1000

# ---------------------------------------------------------------------------
# Photo constraints
# ---------------------------------------------------------------------------
MAX_PHOTO_SIZE_MB: int = 5
MAX_PHOTO_SIZE_BYTES: int = MAX_PHOTO_SIZE_MB * 1024 * 1024
ALLOWED_PHOTO_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png"}
ALLOWED_PHOTO_TYPES: set[str] = {"image/jpeg", "image/png"}
ALLOWED_PHOTO_FORMATS: set[str] = {"JPEG", "PNG"}  # Pillow's Image.format values
MAX_PHOTO_PIXELS: int = 25_000_000
MAX_PHOTO_DIMENSION: int = 8192  # max width or height in pixels
SAVED_PHOTO_MAX_DIMENSION: int = 2048  # max width or height after saving

# ---------------------------------------------------------------------------
# Optional local complaint assistance
# ---------------------------------------------------------------------------
ASSISTANCE_ENABLED: bool = True
ASSISTANCE_INPUT_LIMIT: int = 800
ASSISTANCE_TIMEOUT_SECONDS: int = 30
ASSISTANCE_RATE_LIMIT_SECONDS: int = 20
ASSISTANCE_MODEL: str = "qwen3:4b"
ASSISTANCE_BASE_URL: str = "http://127.0.0.1:11434"
ASSISTANCE_FORM_VERSION: int = 2
ROMAN_LANGUAGES: tuple[str, ...] = ("Roman Punjabi", "Roman Hindi", "English")
SUPPORTED_LANGUAGES: tuple[str, ...] = (
    "Gurmukhi Punjabi",
    "Devanagari Hindi",
    *ROMAN_LANGUAGES,
)

# ---------------------------------------------------------------------------
# Location limits
# ---------------------------------------------------------------------------
MAX_LOCATION_DESCRIPTION_LENGTH: int = 200
MIN_LATITUDE: float = -90.0
MAX_LATITUDE: float = 90.0
MIN_LONGITUDE: float = -180.0
MAX_LONGITUDE: float = 180.0

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH: str = os.path.join(_PROJECT_ROOT, "roadsaarthi.db")

# ---------------------------------------------------------------------------
# Uploads directory
# ---------------------------------------------------------------------------
UPLOADS_DIR: str = os.path.join(_PROJECT_ROOT, "uploads")
