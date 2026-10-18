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

## Optional multilingual complaint assistance

The assistance option is off until a reporter explicitly opts in and requests it.
Gurmukhi and Devanagari are detected from Unicode script ranges. Roman-script
complaints require a language selection. Per-language keyword rules suggest a
category first; every category must be confirmed by the reporter. Punjabi
summaries are unavailable. Other supported languages can receive a short
English summary beside the original, labeled as automatic and possibly wrong.

When requested, complaint text is sent to Ollama on this computer at the fixed
localhost address `http://127.0.0.1:11434`. No external AI endpoint is used.
The model is unloaded after a call; assistance input is capped at 800 characters,
thinking is disabled, and the request timeout is 30 seconds. Model failure does
not prevent manual reporting. Complaint text is not written to application logs.

### Database migration backup and restore

Before manually migrating, stop the app and copy `roadsaarthi.db` to a safe
location. On first startup with the Phase 2 schema, the app also creates
`roadsaarthi.db.pre_phase2.bak` before adding the new nullable columns. If that
name already exists, it uses a timestamped `.pre_phase2.<timestamp>.bak` name.
Keep the backup until the migrated database has been checked. To restore, stop
the app, preserve the current database for diagnosis, then copy the backup back
as `roadsaarthi.db` and restart.

### Synthetic category evaluation

`tests/data/sample_complaints.csv` contains 10 synthetic examples per supported
language. It is a small smoke-test set, not evidence of production accuracy.
Run rules-only metrics with:

```powershell
python scripts/evaluate_categories.py
```

To opt in to sending unmatched synthetic examples to the local Ollama model:

```powershell
python scripts/evaluate_categories.py --with-model
```

The report shows per-language and overall accuracy and coverage. It does not
print complaint text. Review evaluation performance before changing language
or summary safeguards.
