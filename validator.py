from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

from extractor import ExtractedPricing


TOLERANCE = 0.03  # Absorbs minor GST differences / rounding


# Explicit status codes to tell the UI WHY a comparison is in its current state
CODE_MATCHES_LISTED_PLAN = "MATCHES_LISTED_PLAN"
CODE_NO_LISTED_MATCH = "NO_LISTED_MATCH"
CODE_NO_PRICE_FOUND = "NO_PRICE_FOUND"
CODE_GATE_MISMATCH = "GATE_MISMATCH"
CODE_IDENTITY_UNVERIFIED = "IDENTITY_UNVERIFIED"
CODE_SEARCH_THROTTLED = "SEARCH_THROTTLED"


@dataclass
class ValidationReport:
    confidence_tier: Literal["HIGH", "MEDIUM", "UNAVAILABLE"]
    reason_code: str
    decision_reason: str
    currency_checked: bool = False
    currency_match: bool = False
    cadence_checked: bool = False
    cadence_match: bool = False
    matched_plan: Optional[str] = None
    potential_difference: Optional[float] = None
    cheaper_options: List[
        Tuple[str, float, float, Optional[str]]
    ] = field(default_factory=list)


def validate_comparison(
    user_amount: float,
    user_currency: str,
    user_cadence: str,
    extracted: ExtractedPricing,
) -> ValidationReport:

    # 1. Extraction empty or failed
    if extracted.extraction_confidence != "high" or not extracted.plans:
        return ValidationReport(
            confidence_tier="UNAVAILABLE",
            reason_code=CODE_NO_PRICE_FOUND,
            decision_reason=(
                "Public search ran, but no clear subscription prices "
                "could be extracted."
            ),
            currency_checked=False,
            currency_match=False,
            cadence_checked=False,
            cadence_match=False,
        )

    # 2. Gate check: Currency and Cadence
    comparable = [
        p
        for p in extracted.plans
        if p.currency.upper() == user_currency.upper()
        and p.billing_period == user_cadence
    ]

    if not comparable:
        return ValidationReport(
            confidence_tier="UNAVAILABLE",
            reason_code=CODE_GATE_MISMATCH,
            decision_reason=(
                f"Prices found, but none in {user_currency}/{user_cadence}. "
                "Comparison rejected to prevent false calculation."
            ),
            currency_checked=True,
            currency_match=any(
                p.currency.upper() == user_currency.upper()
                for p in extracted.plans
            ),
            cadence_checked=True,
            cadence_match=any(
                p.billing_period == user_cadence
                for p in extracted.plans
            ),
        )

    # 3. Plan Matching
    nearest = min(
        comparable,
        key=lambda p: abs(p.price - user_amount),
    )

    cheaper = sorted(
        [
            (
                p.tier,
                p.price,
                round(user_amount - p.price, 2),
                p.eligibility,
            )
            for p in comparable
            if p.price < user_amount * (1 - TOLERANCE)
        ],
        key=lambda t: t[1],
        reverse=True,
    )

    if abs(nearest.price - user_amount) <= TOLERANCE * nearest.price:
        return ValidationReport(
            confidence_tier="HIGH",
            reason_code=CODE_MATCHES_LISTED_PLAN,
            decision_reason=(
                f"Your charge matches the listed {nearest.tier} price. "
                "Not an overcharge; any cheaper tiers are downgrade options."
            ),
            currency_checked=True,
            currency_match=True,
            cadence_checked=True,
            cadence_match=True,
            matched_plan=nearest.tier,
            potential_difference=0.0,
            cheaper_options=cheaper,
        )

    return ValidationReport(
        confidence_tier="MEDIUM",
        reason_code=CODE_NO_LISTED_MATCH,
        decision_reason=(
            f"Your charge does not match any current listed "
            f"{user_cadence} price "
            f"(nearest: {nearest.tier} at ₹{nearest.price:g})."
        ),
        currency_checked=True,
        currency_match=True,
        cadence_checked=True,
        cadence_match=True,
        matched_plan=None,
        potential_difference=round(user_amount - nearest.price, 2),
        cheaper_options=cheaper,
    )