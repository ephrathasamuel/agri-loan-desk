from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app.summary import MODEL, SummaryError, _for_model, summarise
from app.risk.engine import assess
from datetime import date


def assessment(daily):
    inputs = {"crop": "teff", "soil": "clay", "planting_month": 7, "planting_day": 10,
              "area_ha": 1.0, "loan_amount_etb": 15000}
    result = assess(inputs, daily, today=date(2026, 11, 2))
    result["field"] = {"lat": 8.75, "lon": 38.98, "area_ha": 1.0, "area_source": "entered"}
    return {"farmer_name": "Abebe", "farmer_ref": None, "result": result}


class FakeMessages:
    def __init__(self, response=None, exc=None):
        self.response, self.exc, self.kwargs = response, exc, None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.exc:
            raise self.exc
        return self.response


def fake_client(messages):
    return SimpleNamespace(beta=SimpleNamespace(messages=messages))


def text_response(text, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, model=MODEL,
                           content=[SimpleNamespace(type="text", text=text)])


def test_summary_sends_only_computed_numbers(daily):
    messages = FakeMessages(text_response("Overall:\n- ok"))
    note = summarise(assessment(daily), "am", client=fake_client(messages))
    assert note == {"text": "Overall:\n- ok", "model": MODEL, "language": "Amharic"}
    kw = messages.kwargs
    assert kw["model"] == "claude-opus-5-5"
    assert "Amharic" in kw["messages"][0]["content"]
    assert "Do not approve or reject" in kw["system"]
    assert kw["fallbacks"] == "default"


def test_payload_trims_long_tables(daily):
    payload = _for_model(assessment(daily))
    assert set(payload["climate_risk"]["seasons"][0]) == {"year", "season_rain_mm", "index_rain_mm", "yield_loss", "dry"}
    assert all(y["flag"] for y in payload["insurance"]["years"])
    assert payload["crop"]["notes"]  # the teff approximation note reaches the model


def test_refusal_and_errors_become_summary_errors(daily):
    with pytest.raises(SummaryError, match="declined"):
        summarise(assessment(daily), client=fake_client(FakeMessages(text_response("", stop="refusal"))))
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.AuthenticationError("bad key", response=httpx.Response(401, request=request), body=None)
    with pytest.raises(SummaryError, match="rejected"):
        summarise(assessment(daily), client=fake_client(FakeMessages(exc=err)))
