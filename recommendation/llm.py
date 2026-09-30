"""
Optional phrasing layer — turns the structured output of engine.py into a
short plain-language advisory a farmer can read. Falls back to a template
if no Gemini key is set, so the app never breaks without it.

This layer NEVER makes the decision — engine.py already decided what to
recommend. This only rewrites it in plain language. Keep it that way:
if the LLM starts inventing new advice, that's a bug, not a feature.
"""
import os

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")


def phrase_advisory(recommendation: dict, language: str = "English") -> str:
    actions = recommendation.get("recommended_actions", [])
    plot_code = recommendation.get("plot_code", "this plot")

    if not GEMINI_AVAILABLE or not GEMINI_KEY:
        return _template_fallback(recommendation)

    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = (
        f"Rewrite these farm recommendations for plot {plot_code} as 2-3 short, "
        f"plain sentences in {language}, for a farmer with no technical background. "
        f"Do not add any advice beyond what is listed. Do not use jargon.\n\n"
        f"Recommendations:\n" + "\n".join(f"- {a}" for a in actions)
    )

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return _template_fallback(recommendation)


def _template_fallback(recommendation: dict) -> str:
    actions = recommendation.get("recommended_actions", [])
    if not actions:
        return "No specific action needed right now."
    return " ".join(actions)
