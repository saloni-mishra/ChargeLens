import os
import re
from typing import List, Literal
from pydantic import BaseModel
from google import genai

class Plan(BaseModel):
    tier: str
    price: float
    currency: str
    billing_period: Literal["monthly", "annual", "quarterly"]
    eligibility: str | None = None

class ExtractedPricing(BaseModel):
    plans: List[Plan]
    extraction_confidence: Literal["high", "unclear", "not_found"]

PRICE_RE = re.compile(r"(₹|Rs\.?|INR)\s?\d", re.I)
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
PROMPT = """Extract current subscription plan prices for {service} in India from these search snippets.

Use ONLY prices explicitly written in the snippets. Never guess. Skip anything unclear.

Return every distinct plan: tier name, price, ISO currency, billing_period (monthly/annual/quarterly).

If a plan has eligibility restrictions such as student, senior, military, family, education, or similar, include the restriction in eligibility. Otherwise use null.

Set extraction_confidence to "high" only if at least one plan price is stated clearly.

Snippets:

{snippets}"""

_client = None

def _grounded(price: float, text: str) -> bool:
    """Verifies that the numeric price literally exists in the search snippet text."""
    n = int(price) if float(price).is_integer() else price
    return any(
        re.search(rf"(?<![\d,]){re.escape(form)}(?!\d)", text)
        for form in {str(n), f"{n:,}"}
    )

def extract_pricing_structure(service: str, snippets: str) -> ExtractedPricing:
    if not snippets or not PRICE_RE.search(snippets):
        return ExtractedPricing(plans=[], extraction_confidence="not_found")
        
    global _client
    try:
        _client = _client or genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resp = _client.models.generate_content(
            model=MODEL,
            contents=PROMPT.format(service=service, snippets=snippets),
            config={
                "response_mime_type": "application/json",
                "response_schema": ExtractedPricing,
                "temperature": 0
            },
        )
        result = resp.parsed or ExtractedPricing.model_validate_json(resp.text)
    except Exception:
        return ExtractedPricing(plans=[], extraction_confidence="unclear")

    # Hard grounding filter: drop hallucinated plans
    result.plans = [p for p in result.plans if _grounded(p.price, snippets)]
    if not result.plans:
        result.extraction_confidence = "not_found"
        
    return result