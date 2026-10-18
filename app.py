"""RoadSaarthi AI — Streamlit entry point for hazard report submission."""

import os

import streamlit as st

from roadsaarthi import config
from roadsaarthi.complaint_assistance import get_assistance, PUNJABI_LANGUAGES
from roadsaarthi.geolocation import ERROR_MESSAGES, location_button, reading_to_fields
from roadsaarthi.language import detect_script, resolve_language, ROMAN, UNKNOWN
from roadsaarthi.storage import init_db, save_report
from roadsaarthi.validation import (
    validate_category,
    validate_description,
    validate_location,
    validate_photo,
)


def main() -> None:
    st.set_page_config(
        page_title="RoadSaarthi AI — Report a Hazard",
        page_icon="\U0001f6a7",
        layout="centered",
    )

    st.session_state.setdefault("report_form_version", config.ASSISTANCE_FORM_VERSION)
    st.session_state.setdefault("last_submitted_report_id", None)
    form_version = st.session_state.report_form_version

    # Ensure the database table exists on every run.
    init_db()

    # ── Header ──────────────────────────────────────────────────────────
    st.title("\U0001f6a7 RoadSaarthi AI")
    st.subheader("Report a Road Hazard")
    if st.session_state.last_submitted_report_id is not None:
        st.success(
            f"\u2705 Report submitted successfully!\n\n"
            f"**Report ID:** {st.session_state.last_submitted_report_id}\n\n"
            f"**Status:** Unverified \u2014 a review is pending."
        )
    st.markdown(
        "Describe the hazard you've spotted. Your report is saved for review."
    )
    st.divider()

    # ── Category (outside form so it renders immediately) ───────────────
    # ── Description ─────────────────────────────────────────────────────
    description = st.text_area(
        "Description *",
        max_chars=config.MAX_DESCRIPTION_LENGTH,
        height=120,
        help=(
            f"Describe the hazard in "
            f"{config.MIN_DESCRIPTION_LENGTH}\u2013"
            f"{config.MAX_DESCRIPTION_LENGTH} characters."
        ),
        placeholder=(
            "e.g. Large pothole in the middle of the left lane, "
            "about 1 foot deep. Vehicles are swerving to avoid it."
        ),
        key=f"description_{form_version}",
    )

    script = detect_script(description)
    roman_language = None
    language_key = f"language_v{config.ASSISTANCE_FORM_VERSION}_{form_version}"
    if script == ROMAN:
        roman_language = st.selectbox(
            "Complaint language *", options=[""] + list(config.ROMAN_LANGUAGES),
            key=language_key,
        )
    elif script == UNKNOWN and description.strip():
        st.warning("Language could not be resolved from its script. Choose a language.")
        roman_language = st.selectbox(
            "Complaint language *", options=[""] + list(config.SUPPORTED_LANGUAGES),
            key=language_key,
        )
    language = resolve_language(description, roman_language)
    assistance_key = f"assistance_v{config.ASSISTANCE_FORM_VERSION}_{form_version}"
    category_key = f"category_v{config.ASSISTANCE_FORM_VERSION}_{form_version}"
    confirmation_key = f"category_confirmed_v{config.ASSISTANCE_FORM_VERSION}_{form_version}"
    context_key = f"assistance_context_v{config.ASSISTANCE_FORM_VERSION}_{form_version}"
    context = (description, language)
    if st.session_state.get(context_key) != context:
        st.session_state.pop(assistance_key, None)
        st.session_state.pop(category_key, None)
        st.session_state.pop(confirmation_key, None)
        st.session_state[context_key] = context
    opted_in = False
    if language:
        opted_in = st.checkbox(
            "Use optional local AI assistance", value=False,
            key=f"optin_v{config.ASSISTANCE_FORM_VERSION}_{form_version}",
            help="The complaint is sent to Ollama on this computer only after you request assistance.",
        )
        if opted_in:
            st.caption("Your text is sent only to the local model when you request assistance.")
            if language in PUNJABI_LANGUAGES:
                rules_result = get_assistance(description, language)
                if rules_result["category"]:
                    st.info(f"Category suggested by rules: **{rules_result['category']}**")
                st.info("Summary not available.")
                st.session_state[assistance_key] = {
                    **rules_result, "source": description, "language": language
                }
            elif st.button("Get category suggestion and summary",
                           key=f"assist_button_v{config.ASSISTANCE_FORM_VERSION}_{form_version}"):
                if description:
                    with st.spinner("Loading local model…"):
                        st.session_state[assistance_key] = {
                            **get_assistance(description, language),
                            "source": description, "language": language,
                        }

    stored_assistance = st.session_state.get(assistance_key) or {}
    assistance = (
        stored_assistance
        if (opted_in and stored_assistance.get("source") == description
            and stored_assistance.get("language") == language)
        else {}
    )
    if assistance.get("error"):
        st.warning(assistance["error"])
    if assistance.get("summary"):
        left, right = st.columns(2)
        with left:
            st.markdown("**Your original complaint**")
            st.write(description)
        with right:
            st.markdown("**Automatic English summary (may be wrong)**")
            st.write(assistance["summary"])
    options = [""] + list(config.HAZARD_CATEGORIES)
    proposed = assistance.get("category")
    initial = options.index(proposed) if proposed in options else 0
    category = st.selectbox(
        "Hazard Category *", options=options, index=initial,
        help="Confirm or change the suggested category.",
        key=category_key,
    )
    category_confirmed = st.checkbox(
        "I confirm this category",
        key=confirmation_key,
    )

    # ── Photo (optional) ────────────────────────────────────────────────
    st.markdown("**Photo** (optional)")
    uploaded_file = st.file_uploader(
        "Attach a photo of the hazard",
        type=["jpg", "jpeg", "png"],
        help=f"JPEG or PNG, max {config.MAX_PHOTO_SIZE_MB} MB.",
        label_visibility="collapsed",
        key=f"photo_{form_version}",
    )

    # ── Location (optional, behind consent gate) ────────────────────────
    st.divider()
    location_consent = st.checkbox(
        "I want to share the location of this hazard (optional)",
        value=False,
        key=f"location_consent_{form_version}",
    )

    location_description = None
    latitude = None
    longitude = None
    lat_error = False
    lon_error = False

    if location_consent:
        st.info(
            "\U0001f4cd Your location will be stored with this report "
            "to help authorities find the hazard. It will not be "
            "shared publicly."
        )

        # Apply a one-time component trigger before creating its widgets.
        # Streamlit permits setting widget state before that widget is
        # instantiated in the current run.
        accuracy_key = f"location_accuracy_{form_version}"
        accuracy = st.session_state.get(accuracy_key)
        component_v2 = getattr(
            getattr(getattr(st, "components", None), "v2", None),
            "component",
            None,
        )
        if component_v2 is None:
            st.caption("Location button unavailable; manual entry is used.")
        else:
            reading_result = location_button(key=f"location_button_{form_version}")
            raw_reading = getattr(reading_result, "reading", None)
            if raw_reading is not None:
                fields_or_error = reading_to_fields(raw_reading)
                if isinstance(fields_or_error, str):
                    st.warning(ERROR_MESSAGES[fields_or_error])
                else:
                    st.session_state[f"latitude_{form_version}"] = fields_or_error[
                        "latitude"
                    ]
                    st.session_state[f"longitude_{form_version}"] = fields_or_error[
                        "longitude"
                    ]
                    accuracy = fields_or_error["accuracy"]
                    if accuracy is not None:
                        st.session_state[accuracy_key] = accuracy
                    else:
                        st.session_state.pop(accuracy_key, None)

        st.caption("These are your current position. Edit them if the hazard is elsewhere.")
        if accuracy is not None:
            st.info(f"Accuracy about {accuracy:.0f} m")
            if accuracy > 100:
                st.warning("Low accuracy: check the coordinates or edit them.")

        location_description = st.text_input(
            "Location description *",
            max_chars=config.MAX_LOCATION_DESCRIPTION_LENGTH,
            placeholder='e.g. "Near Bus Stand, Jalandhar"',
            help="A short description of where the hazard is.",
            key=f"location_description_{form_version}",
        )

        col1, col2 = st.columns(2)
        with col1:
            lat_input = st.text_input(
                "Latitude (optional)",
                placeholder="e.g. 31.3260",
                help=(
                    "You can get coordinates by right-clicking "
                    "on Google Maps."
                ),
                key=f"latitude_{form_version}",
            )
        with col2:
            lon_input = st.text_input(
                "Longitude (optional)",
                placeholder="e.g. 75.5762",
                help=(
                    "You can get coordinates by right-clicking "
                    "on Google Maps."
                ),
                key=f"longitude_{form_version}",
            )

        # Parse lat/lon text to float
        if lat_input and lat_input.strip():
            try:
                latitude = float(lat_input)
            except ValueError:
                lat_error = True

        if lon_input and lon_input.strip():
            try:
                longitude = float(lon_input)
            except ValueError:
                lon_error = True

    st.divider()

    # ── Submit button ───────────────────────────────────────────────────
    submitted = st.button(
        "\U0001f6a8 Submit Report", width="stretch", type="primary"
    )

    # ── Process submission ──────────────────────────────────────────────
    if submitted:
        errors: list[str] = []

        # Category
        ok, msg = validate_category(category)
        if not ok:
            errors.append(msg)
        if not category_confirmed:
            errors.append("Please confirm the hazard category.")

        # Description
        ok, msg = validate_description(description)
        if not ok:
            errors.append(msg)

        # Photo
        photo_data: bytes | None = None
        photo_extension: str | None = None

        if uploaded_file is not None:
            photo_bytes = uploaded_file.getvalue()
            ok, msg = validate_photo(
                file_name=uploaded_file.name,
                file_type=uploaded_file.type or "",
                file_size=len(photo_bytes),
                file_data=photo_bytes,
            )
            if not ok:
                errors.append(msg)
            else:
                photo_data = photo_bytes
                photo_extension = os.path.splitext(uploaded_file.name)[1]

        # Location
        if lat_error or lon_error:
            errors.append("Latitude and longitude must be valid numbers.")
        else:
            ok, msg = validate_location(
                consent=location_consent,
                location_description=location_description,
                latitude=latitude,
                longitude=longitude,
            )
            if not ok:
                errors.append(msg)

        # Show errors or save
        if errors:
            for err in errors:
                st.error(err)
        else:
            try:
                report_id = save_report(
                    category=category,
                    description=description,
                    photo_data=photo_data,
                    photo_extension=photo_extension,
                    location_consent=location_consent,
                    location_description=location_description,
                    latitude=latitude,
                    longitude=longitude,
                    summary=assistance.get("summary"),
                    assistant_used=bool(assistance.get("model") or (
                        language in PUNJABI_LANGUAGES and assistance.get("category")
                    )),
                    ai_model=assistance.get("model"),
                )
                st.session_state.last_submitted_report_id = report_id
                st.session_state.pop(f"location_accuracy_{form_version}", None)
                st.session_state.report_form_version += 1
                st.rerun()
            except Exception:
                st.error(
                    "Something went wrong while saving your report. "
                    "Please try again."
                )


if __name__ == "__main__":
    main()
