# RoadSaarthi AI

Road-safety platform where citizens report road hazards using GPS-assisted
reports and photos.  The app helps identify the responsible authority, shows
verified hazards on a community map, detects duplicate reports, and gives
authorities a dashboard to review and prioritise.

> **Milestone 1** — minimal local app: submit a hazard report (category,
> description, optional photo, optional location) and store it in SQLite.

## Prerequisites

- **Python 3.12** (check with `py -3.12 --version`)

## Setup

```powershell
# 1. Create a virtual environment
py -3.12 -m venv .venv

# 2. Activate it
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

## Run the app

```powershell
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

Browser geolocation works only on HTTPS or on localhost. A phone demo opened
over a plain local network IP address will not be able to request its location;
use manual coordinate entry in that setup.

## Run the tests

```powershell
pytest tests/ -v
```

## Project structure

```
roadsaarthi ai/
├── .streamlit/
│   └── config.toml          # Streamlit server config (upload limit)
├── app.py                    # Streamlit UI entry point
├── roadsaarthi/              # Application package
│   ├── __init__.py
│   ├── config.py             # Constants (categories, limits, paths)
│   ├── validation.py         # Pure input-validation functions
│   ├── geolocation.py        # Browser geolocation component and reading parser
│   └── storage.py            # SQLite + photo persistence
├── tests/
│   ├── __init__.py
│   ├── test_validation.py    # Validation unit tests
│   ├── test_geolocation.py   # Geolocation reading parser tests
│   └── test_storage.py       # Storage unit tests
├── requirements.txt          # Pinned dependencies
├── README.md                 # This file
└── .gitignore
```

Runtime artifacts (not committed):
- `roadsaarthi.db` — SQLite database
- `uploads/` — saved photos (EXIF stripped, UUID filenames)
