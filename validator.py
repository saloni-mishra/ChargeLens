from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple
from extractor import ExtractedPricing

TOLERANCE = 0.03  # Absorbs minor GST differences / rounding

@dataclass
class ValidationReport:
    confidence_tier: Literal["HIGH", "MEDIUM", "UNAVAILABLE"]
    finding: str
    decision_reason: str
    matched_plan: Optional[str] = None
    potential_difference: Optional[float] = None
    cheaper_options: List[Tuple[str, float, float]] = field(default_factory=list)

def validate_comparison(user_amount: float, user_currency: str, user_cadence: str,
                        extracted: ExtractedPricing) -> ValidationReport:
    if extracted.extraction_confidence != "high" or not extracted.plans:
        return ValidationReport(
            "UNAVAILABLE", "NO_COMPARISON",
            "No clearly stated prices found in the search evidence."
        )

    comparable = [
        p for p in extracted.plans
        if p.currency.upper() == user_currency.upper()
        and p.billing_period == user_cadence
    ]
    
    if not comparable:
        return ValidationReport(
            "UNAVAILABLE", "NO_COMPARISON",
            f"Prices found, but none in {user_currency}/{user_cadence}. "
            "We never convert currencies or divide annual prices."
        )

    nearest = min(comparable, key=lambda p: abs(p.price - user_amount))
    cheaper = sorted(
        [
            (p.tier, p.price, round(user_amount - p.price, 2))
            for p in comparable if p.price < user_amount * (1 - TOLERANCE)
        ],
        key=lambda t: t[1], reverse=True
    )

    if abs(nearest.price - user_amount) <= TOLERANCE * nearest.price:
        return ValidationReport(
            "HIGH", "MATCHES_LISTED_PLAN",
            f"Your charge matches the listed {nearest.tier} price. Not an overcharge; "
            "any cheaper tiers are downgrade options.",
            matched_plan=nearest.tier,
            cheaper_options=cheaper
        )

    return ValidationReport(
        "MEDIUM", "NO_LISTED_MATCH",
        f"Your charge matches no current listed {user_cadence} price "
        f"(nearest: {nearest.tier} at {nearest.price:g}). Could be an older plan, add-ons, "
        "taxes, or incomplete search evidence.",
        potential_difference=round(user_amount - nearest.price, 2),
        cheaper_options=cheaper
    )