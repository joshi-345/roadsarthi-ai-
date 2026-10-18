"""RoadSaarthi AI — Streamlit entry point for hazard report submission."""

import os

import streamlit as st

from roadsaarthi import config
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

    # Ensure the database table exists on every run.
    init_db()

    # ── Header ──────────────────────────────────────────────────────────
    st.title("\U0001f6a7 RoadSaarthi AI")
    st.subheader("Report a Road Hazard")
    st.markdown(
        "Help make roads safer. Describe the hazard you\u2019ve spotted "
        "and we\u2019ll route it to the right authority."
    )
    st.divider()

    # ── Category (outside form so it renders immediately) ───────────────
    category = st.selectbox(
        "Hazard Category *",
        options=[""] + list(config.HAZARD_CATEGORIES),
        index=0,
        help="Select the type of road hazard.",
    )

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
    )

    # ── Photo (optional) ────────────────────────────────────────────────
    st.markdown("**Photo** (optional)")
    uploaded_file = st.file_uploader(
        "Attach a photo of the hazard",
        type=["jpg", "jpeg", "png"],
        help=f"JPEG or PNG, max {config.MAX_PHOTO_SIZE_MB} MB.",
        label_visibility="collapsed",
    )

    # ── Location (optional, behind consent gate) ────────────────────────
    st.divider()
    location_consent = st.checkbox(
        "I want to share the location of this hazard (optional)",
        value=False,
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
        location_description = st.text_input(
            "Location description *",
            max_chars=config.MAX_LOCATION_DESCRIPTION_LENGTH,
            placeholder='e.g. "Near Bus Stand, Jalandhar"',
            help="A short description of where the hazard is.",
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
            )
        with col2:
            lon_input = st.text_input(
                "Longitude (optional)",
                placeholder="e.g. 75.5762",
                help=(
                    "You can get coordinates by right-clicking "
                    "on Google Maps."
                ),
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
        "\U0001f6a8 Submit Report", use_container_width=True, type="primary"
    )

    # ── Process submission ──────────────────────────────────────────────
    if submitted:
        errors: list[str] = []

        # Category
        ok, msg = validate_category(category)
        if not ok:
            errors.append(msg)

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
                )
                st.success(
                    f"\u2705 Report submitted successfully!\n\n"
                    f"**Report ID:** {report_id}\n\n"
                    f"**Status:** Unverified \u2014 a review is pending."
                )
            except Exception:
                st.error(
                    "Something went wrong while saving your report. "
                    "Please try again."
                )


if __name__ == "__main__":
    main()
