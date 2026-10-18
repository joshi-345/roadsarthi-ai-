from roadsaarthi.complaint_assistance import get_assistance, suggest_from_rules, _last_call


def test_rules_match_language_examples():
    assert suggest_from_rules("unusual words", "English") is None
    assert suggest_from_rules("Large pothole by the lane", "English") == "Pothole"
    assert suggest_from_rules("सड़क पर गड्ढा", "Devanagari Hindi") == "Pothole"
    assert suggest_from_rules("sadak par gaddha", "Roman Hindi") == "Pothole"
    assert suggest_from_rules("sadak te khadda", "Roman Punjabi") == "Pothole"
    assert suggest_from_rules("ਸੜਕ ਤੇ ਖੱਡਾ", "Gurmukhi Punjabi") == "Pothole"


def test_punjabi_never_calls_provider_and_has_no_summary():
    def fail(**kwargs):
        raise AssertionError("Punjabi must not use model")
    result = get_assistance("ਸੜਕ ਤੇ ਖੱਡਾ", "Gurmukhi Punjabi", client=fail)
    assert result["category"] == "Pothole"
    assert result["summary"] is None


def test_invalid_model_category_ignored_and_summary_capped():
    _last_call.clear()
    def fake(**kwargs):
        return {"category": "Not a category", "summary": "  " + "x " * 200,
                "model": "fake"}
    result = get_assistance("No matching phrase", "English", client=fake, now=1000)
    assert result["category"] is None
    assert len(result["summary"]) <= 240


def test_rule_category_wins_over_model_category():
    _last_call.clear()
    result = get_assistance("A pothole in the road", "English",
                            client=lambda **kwargs: {"category": "Road Debris", "summary": "Pothole."},
                            now=2000)
    assert result["category"] == "Pothole"


def test_rate_limit_stops_second_provider_call():
    _last_call.clear()
    calls = []
    fake = lambda **kwargs: (calls.append(kwargs) or {"category": "Other", "summary": "A hazard."})
    first = get_assistance("Unmatched first report", "English", client=fake, now=3000)
    second = get_assistance("Unmatched second report", "English", client=fake, now=3001)
    assert first["summary"] == "A hazard."
    assert "wait" in second["error"].lower()
    assert len(calls) == 1


def test_provider_failure_is_generic_and_does_not_log_complaint(caplog):
    _last_call.clear()
    private_text = "synthetic-private-complaint-9173"
    def failing_client(**kwargs):
        raise TimeoutError(private_text)
    result = get_assistance(private_text, "English", client=failing_client, now=4000)
    assert result["error"] == "Local assistance is unavailable. Continue manually."
    assert private_text not in caplog.text
