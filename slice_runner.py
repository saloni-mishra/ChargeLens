import os

from dotenv import load_dotenv

# Must run BEFORE imports to hydrate search/extractor env vars
load_dotenv()

import pandas as pd

from database import init_db, get_cached_pricing, save_pricing_cache
from cleaner import clean_merchant_string
from normalizer import resolve_merchant
from detector import analyze_recurring_patterns
from search import fetch_pricing_evidence
from extractor import extract_pricing_structure, ExtractedPricing
from validator import validate_comparison


SEARCHABLE = {"LOCAL_RULE", "IDENTITY_CACHE"}


def get_evidence(service: str):
    """
    Cache -> Search -> Extract.

    Returns:
        (ExtractedPricing | None, note, provenance)
    """

    cached = get_cached_pricing(service, ttl_days=14)

    if cached:
        try:
            extracted = ExtractedPricing.model_validate_json(
                cached["extracted_json"]
            )

            provenance = {
                "source": "CACHE",
                "query": cached["query_used"],
                "retrieved_at": cached["retrieved_at"],
                "extraction_model": os.getenv(
                    "GEMINI_MODEL",
                    "gemini-2.5-flash",
                ),
                "validation_method": "Deterministic Python validator",
            }

            return (
                extracted,
                f"CACHE ({cached['retrieved_at']})",
                provenance,
            )

        except Exception:
            # Invalid/stale cache entry: fall through to search.
            pass

    query, snippets, url, status = fetch_pricing_evidence(service)

    if snippets is None:
        provenance = {
            "source": status,
            "query": query,
            "retrieved_at": None,
            "extraction_model": os.getenv(
                "GEMINI_MODEL",
                "gemini-2.5-flash",
            ),
            "validation_method": "Deterministic Python validator",
        }

        return None, status, provenance

    extracted = extract_pricing_structure(service, snippets)

    if extracted.extraction_confidence == "high":
        save_pricing_cache(
            service,
            query,
            snippets,
            extracted.model_dump_json(),
        )

        # Get the exact timestamp written to the cache.
        saved = get_cached_pricing(service, ttl_days=14)
        retrieved_at = saved["retrieved_at"] if saved else None
    else:
        retrieved_at = None

    provenance = {
        "source": status,
        "query": query,
        "retrieved_at": retrieved_at,
        "extraction_model": os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        ),
        "validation_method": "Deterministic Python validator",
    }

    return extracted, status, provenance


def print_drawer(item, report, note, provenance):
    print("\n" + "=" * 30 + " EVIDENCE DRAWER " + "=" * 30)

    print(f"Confidence Tier : {report.confidence_tier}")
    print(f"Reason          : {report.decision_reason}")
    print(f"Your Charge     : ₹{item['user_amount']}/{item['cadence']}")
    print(f"Evidence Source : {note}")
    print(f"Search Source   : {provenance.get('source')}")
    print(f"Search Query    : {provenance.get('query')}")
    print(f"Retrieved At    : {provenance.get('retrieved_at')}")
    print(f"Extraction Model: {provenance.get('extraction_model')}")
    print(f"Validation      : {provenance.get('validation_method')}")

    if report.matched_plan:
        print(f"Matched Plan   : {report.matched_plan}")

    if report.potential_difference is not None:
        print(f"Diff vs Nearest : ₹{report.potential_difference:+}")

    for tier, price, saving, eligibility in report.cheaper_options:
        eligibility_note = (
            " (eligibility verification may be required)"
            if eligibility
            else ""
        )

        print(
            f"Cheaper Tier    : {tier}{eligibility_note} "
            f"₹{price:g} (would save ₹{saving:g})"
        )

    print("=" * 77)


def run_vertical_slice():
    init_db()

    df = pd.read_csv("sample_statement.csv")

    df["cleaned"] = df["raw_description"].apply(clean_merchant_string)

    resolved = df["cleaned"].apply(resolve_merchant)

    df["normalized_merchant"] = resolved.apply(lambda t: t[0])

    source_by_merchant = dict(
        zip(
            df["normalized_merchant"],
            resolved.apply(lambda t: t[1]),
        )
    )

    candidates = analyze_recurring_patterns(df)

    print(f"Detected {len(candidates)} recurring charge(s).")

    for item in candidates:
        merchant = item["merchant"]

        print(
            f"\n{merchant}: "
            f"₹{item['user_amount']}/mo, "
            f"recurring confidence "
            f"{item['recurring_confidence']}%"
        )

        if source_by_merchant.get(merchant) not in SEARCHABLE:
            print(
                "  Recurring charge detected; service not identified "
                "locally, so no search was spent."
            )
            continue

        extracted, note, provenance = get_evidence(merchant)

        if extracted is None:
            print(
                f"  Recurring charge confirmed; "
                f"price comparison unavailable ({note})."
            )
            continue

        report = validate_comparison(
            item["user_amount"],
            item["user_currency"],
            item["cadence"],
            extracted,
        )

        print_drawer(
            item,
            report,
            note,
            provenance,
        )


if __name__ == "__main__":
    run_vertical_slice()