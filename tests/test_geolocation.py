"""Tests for the pure browser-reading parser."""

import math

import pytest

from roadsaarthi.geolocation import ERROR_MESSAGES, reading_to_fields


def test_valid_reading_is_rounded_to_five_decimal_places():
    assert reading_to_fields(
        {"latitude": 31.3260123, "longitude": 75.5762345, "accuracy": 12.4}
    ) == {
        "latitude": "31.32601",
        "longitude": "75.57623",
        "accuracy": 12.4,
    }


@pytest.mark.parametrize("reading", [None, {}, {"latitude": 1}, {"longitude": 2}])
def test_missing_reading_or_coordinates_return_safe_error(reading):
    assert reading_to_fields(reading) == "unavailable"


@pytest.mark.parametrize(
    "reading",
    [
        {"latitude": "1", "longitude": 2},
        {"latitude": 1, "longitude": "2"},
        {"latitude": "north", "longitude": 2},
        {"latitude": True, "longitude": 2},
    ],
)
def test_string_or_non_numeric_coordinates_are_rejected(reading):
    assert reading_to_fields(reading) == "unavailable"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_coordinates_are_rejected(value):
    assert reading_to_fields({"latitude": value, "longitude": 1}) == "unavailable"
    assert reading_to_fields({"latitude": 1, "longitude": value}) == "unavailable"
    assert reading_to_fields(
        {"latitude": 1, "longitude": 2, "accuracy": value}
    ) == "unavailable"


@pytest.mark.parametrize("accuracy", ["5", "unknown", True, -1])
def test_invalid_accuracy_is_rejected(accuracy):
    assert reading_to_fields(
        {"latitude": 1, "longitude": 2, "accuracy": accuracy}
    ) == "unavailable"


@pytest.mark.parametrize(
    ("latitude", "longitude"), [(91, 0), (-91, 0), (0, 181), (0, -181)]
)
def test_out_of_range_coordinates_are_rejected(latitude, longitude):
    assert reading_to_fields({"latitude": latitude, "longitude": longitude}) == "unavailable"


def test_coordinate_boundaries_are_accepted():
    assert reading_to_fields({"latitude": 90, "longitude": 180}) == {
        "latitude": "90.00000",
        "longitude": "180.00000",
        "accuracy": None,
    }
    assert reading_to_fields({"latitude": -90, "longitude": -180}) == {
        "latitude": "-90.00000",
        "longitude": "-180.00000",
        "accuracy": None,
    }


def test_missing_accuracy_does_not_reject_coordinates():
    assert reading_to_fields({"latitude": 1.25, "longitude": 2.5}) == {
        "latitude": "1.25000",
        "longitude": "2.50000",
        "accuracy": None,
    }


@pytest.mark.parametrize("code", ["denied", "unavailable", "timeout"])
def test_browser_error_codes_have_plain_language_messages(code):
    assert reading_to_fields({"error": code}) == code
    assert ERROR_MESSAGES[code]


def test_untrusted_error_code_is_safely_rejected():
    assert reading_to_fields({"error": "unexpected"}) == "unavailable"
