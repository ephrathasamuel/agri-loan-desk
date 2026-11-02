"""Plain-language summary of an assessment for the loan officer, by Claude.

The model only explains numbers the risk engine has already calculated; it is
told not to produce new figures or make the credit decision.
"""

import json

import anthropic

MODEL = "claude-opus-5-5"
LANGUAGES = {"en": "English", "am": "Amharic"}

SYSTEM_PROMPT = """You write short briefing notes for agricultural loan officers at an Ethiopian bank or microfinance institution.

You receive an assessment that has already been calculated: climate risk from more than 30 years of NASA POWER weather history for the farmer's field, a FAO-56 water balance with FAO-33 yield response, a suggested loan structure, and a weather-index drought insurance design. Your job is to explain it, not to recalculate it.

Rules:
- Use only numbers that appear in the assessment. Do not invent, estimate or derive new figures. If something is not in the assessment, say it is not available.
- Do not approve or reject the loan. The officer decides; you explain what the numbers show.
- Clearly separate measured history (rainfall, simulated seasons) from assumptions (yield, price, repayment share, interest rate, loading). Name the assumptions that matter most for this case.
- Mention basis risk honestly: past bad seasons the insurance would not have paid for, and payouts in years with little loss.
- Mention any crop notes (for example approximations for teff).
- Structure the note with these headings, each on its own line ending with a colon: "Overall:", "Climate risk:", "Loan:", "Insurance:", "Assumptions to check:", "Questions to ask the farmer:".
- Under each heading write two to four short lines starting with "- ".
- Plain text only: no markdown symbols other than the "- " at the start of lines. Money is in Ethiopian birr (ETB)."""


class SummaryError(Exception):
    pass


def _for_model(assessment):
    result = assessment["result"]
    climate = dict(result["climate"])
    # Year-by-year detail is useful but long; keep the fields the note needs.
    climate["seasons"] = [
        {k: s[k] for k in ("year", "season_rain_mm", "index_rain_mm", "yield_loss", "dry")}
        for s in climate["seasons"]
    ]
    insurance = dict(result["insurance"])
    insurance["years"] = [y for y in insurance["years"] if y["flag"]]
    return {
        "farmer": {"name": assessment["farmer_name"], "reference": assessment.get("farmer_ref")},
        "crop": result["crop"],
        "soil": result["soil"],
        "field": result["field"],
        "climate_risk": climate,
        "loan": result["loan"],
        "insurance": insurance,
        "assumptions": result["assumptions"],
    }


def summarise(assessment, language="en", api_key=None, client=None):
    if language not in LANGUAGES:
        language = "en"
    client = client or anthropic.Anthropic(api_key=api_key or None)
    user = (
        f"Write the briefing note in {LANGUAGES[language]}.\n\n"
        "Assessment (JSON):\n" + json.dumps(_for_model(assessment), ensure_ascii=False, indent=1)
    )
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": "medium"},
            # If the model declines, the API retries on Anthropic's recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as exc:
        raise SummaryError("The AI key was rejected. Check ANTHROPIC_API_KEY.") from exc
    except anthropic.RateLimitError as exc:
        raise SummaryError("The AI service is busy (rate limit). Try again in a minute.") from exc
    except anthropic.APIConnectionError as exc:
        raise SummaryError("Could not reach the AI service. Check the connection.") from exc
    except anthropic.APIStatusError as exc:
        raise SummaryError(f"The AI service returned an error ({exc.status_code}).") from exc

    if response.stop_reason == "refusal":
        raise SummaryError("The AI declined to write this note. The calculated assessment is still valid.")
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise SummaryError("The AI returned an empty note. Try again.")
    return {"text": text, "model": response.model, "language": LANGUAGES[language]}
