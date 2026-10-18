# Phase 2 Plan: Multilingual Complaint Assistance

## Goal and constraints

Add optional, human-reviewed assistance to reports while preserving the reporter's description exactly as entered or last edited. The locally tested `qwen3:4b` on Ollama 0.40.6 misidentified both Gurmukhi and Roman Punjabi as Hindi and hallucinated “at night” in a Hindi complaint summary. Therefore the model must not detect language or rewrite the saved description. Punjabi summaries remain off until evaluation supports enabling them. Target hardware includes laptops with 8 GB RAM.

No external AI API is in scope. Ollama is called only at a fixed localhost URL. The feature is opt-in, rate-limited, and must never log complaint text. Take a database backup before applying the additive, idempotent migration.

## Functional design

1. **Language selection**
   - Determine Gurmukhi and Devanagari from deterministic Unicode script ranges in code; do not ask the model to identify language.
   - For Roman-script complaints, require a language dropdown selection (Roman Punjabi, Hindi, or English as applicable to the supported form). Treat mixed or inconclusive scripts conservatively and require user selection rather than guessing.
   - Keep the selected language explicit through category rules, fallback, and summary eligibility.

2. **Category suggestion**
   - Implement deterministic keyword rules separately for Gurmukhi Punjabi, Devanagari Hindi, Roman Punjabi, Roman Hindi, and English, mapped to the existing fixed category set.
   - If a rule matches, show its suggested category. If no rule matches, use the single model provider function to suggest a category, subject to opt-in and rate limiting.
   - The reporter always confirms or changes the category before submission. The model output is a suggestion only; validate it against the fixed category allowlist and fall back safely on invalid output, timeout, or provider failure.
   - For Punjabi, display the category suggested by rules and “Summary not available.” Do not use model category fallback for Punjabi unless explicitly enabled by a later reviewed plan.

3. **Description and summary**
   - Remove `cleaned_complaint` from the design. Never replace, normalize, or save a model-rewritten version of the complaint.
   - Save the exact text the reporter wrote or edited as the report description. Do not trim or normalize the stored value beyond input validation required to reject invalid/empty input; define this invariant in storage tests.
   - The model may produce only a short English summary. Show it beside the original complaint with a clear note: “Automatic summary; may be wrong.” Never use it as the description or imply it is a translation verified by the reporter.
   - Disable summaries for all Punjabi inputs until the Punjabi summary evaluation passes an explicitly reviewed acceptance threshold. For this phase, the Punjabi UI says “Summary not available.”

4. **Model/provider and laptop constraints**
   - Create one provider function as the only model-call boundary, so a different model/provider can later replace Ollama without changes to UI, rules, or storage contracts.
   - Keep the Ollama base URL as a code constant pointing to localhost; never accept a URL from users or form fields.
   - Configure each call to unload the model afterward using Ollama `keep_alive` (zero duration), disable thinking mode, cap complaint input length, and set a configurable request timeout. Exact input cap and timeout should be chosen and documented during implementation based on usability and 8 GB laptop behavior.
   - Display a brief loading note while a model request is running. Provider errors/timeouts must leave the original complaint intact and allow normal manual category confirmation/submission.
   - Rate-limit assistance requests and avoid repeated calls on Streamlit reruns; make opt-in explicit and do not call the provider until the user opts in and requests assistance.

5. **Persistence and migration**
   - Add nullable fields `original_text`, `summary`, `assistant_used`, and `ai_model` through an additive, idempotent SQLite migration. Existing reports remain readable and retain existing data.
   - Back up the database before running the migration; document the backup path and restore procedure. Do not overwrite or delete the original database as part of backup.
   - Store the reporter-authored description unchanged. Record whether assistance was used and the model identifier when applicable. Persist the generated summary only when one is produced; never persist model prompts or provider diagnostics containing complaint text.
   - Version Streamlit form/widget keys for the new language, opt-in, category confirmation, and summary widgets so prior session state does not silently bind to the new controls.

## Proposed files

Names are proposed; reuse the current module layout and avoid adding dependencies unless implementation demonstrates a need.

- `roadsaarthi/language.py` — Unicode script detection and Roman-script language selection validation.
- `roadsaarthi/complaint_assistance.py` — per-language keyword rules, fixed-category validation, and assistance orchestration.
- `roadsaarthi/model_provider.py` — single Ollama provider function, localhost constant, timeout, input cap, thinking disabled, unload behavior, and generic failure handling.
- `roadsaarthi/config.py` — assistance limits, allowed values, rate limit, timeout, model options, and versioned widget-key constants.
- `roadsaarthi/storage.py` — additive idempotent migration and persistence fields.
- `app.py` — opt-in, language selection, loading note, suggestions, confirmation, original/summary display, and Punjabi summary-unavailable state.
- `tests/data/sample_complaints.csv` — at least 10 synthetic complaints per language: Gurmukhi Punjabi, Devanagari Hindi, Roman Punjabi, Roman Hindi, and English; include expected fixed category for each row. No real or copied personal complaints.
- `scripts/evaluate_categories.py` — deterministic report of category accuracy for rules alone versus rules plus model on the labeled CSV. Report counts and accuracy by language and overall; keep model calls opt-in/configurable and do not emit complaint text. Define the no-match/fallback denominator clearly and disclose small synthetic-set limitations.
- `tests/test_language.py` — Unicode range/script detection and Roman language selection cases, including mixed/empty/ambiguous input.
- `tests/test_complaint_assistance.py` — per-language rule matches, no-match behavior, allowlist checks, mandatory user confirmation behavior, and Punjabi restrictions.
- `tests/test_model_provider.py` — fake-client tests for request contract, constant localhost URL, timeout, input cap, disabled thinking, unload setting, error handling, and no complaint text in logs.
- `tests/test_storage.py` — migration idempotence, old database compatibility, exact description preservation, and new nullable fields.
- `tests/test_app_assistance.py` (or existing UI test location) — opt-in/rate-limit flow, versioned widget keys, failure fallback, summary labeling, and Punjabi state.
- `README.md` — local Ollama setup/prerequisites, opt-in behavior, privacy notes, migration backup/restore steps, and evaluation command.

## Automated tests to add or update

- Script detector recognizes Gurmukhi and Devanagari by Unicode ranges without classifying based on model output; Roman-script complaints require the dropdown language.
- Mixed scripts, punctuation-only input, numbers, and unsupported/ambiguous script combinations do not silently become Hindi.
- Rule tests cover each supported language and every fixed category; unmatched text takes the intended fallback path.
- Model category and summary outputs are bounded, validated, and treated as untrusted suggestions; user confirmation remains required.
- Punjabi never invokes summary generation and shows the unavailable state. Model category fallback remains disabled for Punjabi in this phase.
- Summary is English, short, visibly labeled automatic/possibly wrong, displayed next to original, and never substituted for saved description.
- Preserve exact original user text through suggestion, editing, submission, database round-trip, and legacy migration.
- Provider fake-client tests verify localhost-only endpoint, timeout, capped input, thinking disabled, `keep_alive=0`, generic failure handling, and no text in logs. No live Ollama call is required in unit tests.
- Opt-out causes zero provider calls; rate limiting blocks excess requests; reruns do not duplicate calls.
- Migration can run repeatedly and retains legacy report rows. Backup instructions and restore path are manually checked before migration on a copy of the database.
- Evaluation script compares rules-only and rules-plus-model results against `expected_category`; output includes per-language and aggregate metrics and does not print source complaints.

## Manual tests

1. On the 8 GB laptop, submit Gurmukhi Punjabi, Devanagari Hindi, Roman Punjabi, Roman Hindi, and English examples. Confirm script detection and that Roman text requires the dropdown.
2. Use phrases with overlapping terms and mixed scripts; verify no default-to-Hindi behavior and confirm the selected category manually.
3. Opt out, then opt in and request help. Verify no call while opted out, loading note while waiting, and rate-limit behavior on repeated requests.
4. Inspect a Hindi summary against the original, including a complaint without a time-of-day detail. Confirm the summary is labeled as automatic and possibly wrong; the original remains beside it.
5. Enter Punjabi in both scripts. Verify rules can suggest a category, the user confirms it, and the page says “Summary not available” with no summary call.
6. Edit the complaint after assistance and submit. Compare saved description character-for-character with the final edited text; confirm the summary does not overwrite it.
7. Stop Ollama, force a timeout, and return malformed/out-of-category output with a fake provider. The UI should show a generic failure, preserve the complaint, and allow manual submission.
8. On a copy of an existing SQLite database, take a backup, migrate twice, inspect existing and new rows, and rehearse restoring the backup.
9. Observe Ollama memory after each call to confirm the model unloads; repeat with an input at the cap and one over the cap. Confirm response time and memory remain workable on 8 GB.
10. Run the evaluation script and inspect metrics and output for all five language groups; verify it emits no complaint text.

## Privacy impact

- Complaint text is personal report content. When a user opts in and requests assistance, the capped text is sent to the local Ollama service on localhost; disclose this before the action. Do not send it to an external AI API.
- Store the original report text because it is the submitted report. Store an optional model summary and assistance/model metadata only when generated/used. Do not log text, prompts, raw completions, precise locations, or provider errors containing input.
- Synthetic evaluation data must contain no real personal data. Evaluation output should contain metrics only.
- Keep opt-in explicit, rate-limit requests, constrain the local endpoint to a constant, and show that the generated summary can be wrong.

## Risks and mitigations

- **Keyword gaps and ambiguity:** Rules can miss wording or match the wrong category. Maintain per-language examples, return no match when evidence is weak, expose the suggestion for correction, and require reporter confirmation.
- **Hallucinated or omitted summary details:** A short summary can still be wrong. Preserve and display original text, label the summary clearly, disable Punjabi summaries pending evaluation, and never use summary as source of truth.
- **Small synthetic evaluation set:** Ten examples per language is only a smoke-test baseline and cannot establish production accuracy. Report per-language results and expand with consented, reviewed, privacy-safe cases before relaxing safeguards.
- **Roman language ambiguity:** Punjabi and Hindi may overlap in Roman script. Require user selection and do not infer from model output.
- **Resource limits/timeouts:** 8 GB devices may be slow or fail under load. Cap input, disable thinking, unload after each call, set timeout, show loading state, and make manual reporting work without AI.
- **Database migration/backup failure:** A backup can be stale or incomplete. Validate backup creation and restoration on a copy before production migration; migration is additive and repeatable.
- **Privacy through diagnostics or accidental provider configuration:** Keep endpoint fixed at localhost, use generic user errors, and test logs with distinctive synthetic text to ensure it is absent.

## Completion gate

Proceed to implementation only after this plan is reviewed. Keep the feature disabled by default until the fake-client tests, migration/backup rehearsal, language/category tests, manual checks, and evaluation review pass. Do not enable Punjabi summaries until a separately agreed evaluation threshold is met.
