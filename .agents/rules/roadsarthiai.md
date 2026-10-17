---
trigger: always_on
---

# RoadSaarthi AI: Workspace Rules

## Project
Road-safety platform. Citizens report road hazards using GPS-assisted reports and photos.
The app helps identify the responsible authority, shows verified hazards on a community map,
detects duplicate reports, and gives authorities a dashboard to review and prioritise.
GenAI is used for multilingual complaint understanding, evidence-based reports and a
human-approved agent workflow.

## Stack
Python 3.11/3.12, Streamlit, FastAPI, SQLite. No external AI API without my approval.

## Build approach
- I am a beginner. Build one small feature at a time. Propose a plan and wait for approval before coding.
- Small modules, one responsibility each: UI, validation, storage and logic stay separate.
- Reuse existing code. No new file or dependency without a stated reason.
- After each change run the app and tests. Report what passed, failed or is unverified.

## Security and privacy
- Secrets only in environment variables. .env is gitignored. .env.example has fake values only.
- Validate all inputs: type, length, allowed values, file type and size. Parameterized SQL only.
- Location only with explicit consent. No background tracking. Never log precise location or personal data.
- Uploads get generated filenames and are never executed. Handle photo GPS metadata deliberately.
- Show generic errors to users. Details go only to private logs.
- The authority dashboard requires authentication.

## Honesty
- Never fake government submissions, verification, alerts or accident-risk numbers.
- Label unverified reports as unverified. Show uncertainty for authority routing and AI detections.