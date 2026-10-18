"""Browser geolocation component and safe reading parser."""

import math
from typing import Any


_ERROR_CODES = {"denied", "unavailable", "timeout"}

ERROR_MESSAGES = {
    "denied": "Location permission was denied. You can type the coordinates instead.",
    "unavailable": "Your browser could not provide location. You can type the coordinates instead.",
    "timeout": "Location request timed out. You can type the coordinates instead.",
}


def reading_to_fields(reading: Any) -> dict[str, Any] | str:
    """Return display-ready coordinate fields, or a safe error code.

    Accuracy is optional. Invalid readings are rejected without exposing
    browser-provided data in error messages.
    """
    if isinstance(reading, dict) and reading.get("error") in _ERROR_CODES:
        return reading["error"]
    if not isinstance(reading, dict):
        return "unavailable"

    try:
        latitude = reading["latitude"]
        longitude = reading["longitude"]
        if (
            isinstance(latitude, bool)
            or isinstance(longitude, bool)
            or not isinstance(latitude, (int, float))
            or not isinstance(longitude, (int, float))
        ):
            return "unavailable"

        latitude = float(latitude)
        longitude = float(longitude)
        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            return "unavailable"

        accuracy = reading.get("accuracy")
        if accuracy is not None:
            if isinstance(accuracy, bool) or not isinstance(accuracy, (int, float)):
                return "unavailable"
            accuracy = float(accuracy)
            if not math.isfinite(accuracy) or accuracy < 0:
                return "unavailable"

        return {
            "latitude": f"{latitude:.5f}",
            "longitude": f"{longitude:.5f}",
            "accuracy": accuracy,
        }
    except Exception:
        return "unavailable"


_HTML = '<button type="button" id="location-button">Use my current location</button>'

_JS = r"""
export default function(component) {
    const button = component.parentElement.querySelector("#location-button");
    if (!button || button.dataset.bound === "true") return;
    button.dataset.bound = "true";

    button.addEventListener("click", () => {
        if (button.dataset.requesting === "true") return;
        button.dataset.requesting = "true";
        button.disabled = true;
        const finish = (value) => {
            component.setTriggerValue("reading", value);
            button.dataset.requesting = "false";
            button.disabled = false;
        };

        if (!navigator.geolocation) {
            finish({error: "unavailable"});
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => finish({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy
            }),
            (error) => {
                const code = error && error.code;
                finish({error: code === 1 ? "denied" : code === 3 ? "timeout" : "unavailable"});
            },
            {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
        );
    });
}
"""

_COMPONENT = None


def location_button(key: str):
    """Mount the inline geolocation button and return its trigger result."""
    global _COMPONENT
    import streamlit as st

    if _COMPONENT is None:
        _COMPONENT = st.components.v2.component(
            "roadsaarthi_geolocation_button",
            html=_HTML,
            js=_JS,
        )
    return _COMPONENT(key=key, on_reading_change=lambda: None)
