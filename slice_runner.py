from dotenv import load_dotenv
load_dotenv()  # Must run BEFORE imports to hydrate search/extractor env vars

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
    """Cache -> Search -> Extract. Returns (ExtractedPricing | None, note)."""
    cached = get_cached_pricing(service, ttl_days=14)
    if cached:
        try:
            return (
                ExtractedPricing.model_validate_json(cached["extracted_json"]),
                f"CACHE ({cached['retrieved_at']})"
            )
        except Exception:
            pass  # Fall back to fresh search if cached row fails to validate

    query, snippets, url, status = fetch_pricing_evidence(service)
    if snippets is None:
        return None, status

    extracted = extract_pricing_structure(service, snippets)
    if extracted.extraction_confidence != "unclear":
        save_pricing_cache(service, query, snippets, extracted.model_dump_json())

    return extracted, status

def print_drawer(item, r, note):
    print("\n" + "=" * 30 + " EVIDENCE DRAWER " + "=" * 30)
    print(f"Confidence Tier : {r.confidence_tier}   ({r.finding})")
    print(f"Reason          : {r.decision_reason}")
    print(f"Your Charge     : ₹{item['user_amount']}/{item['cadence']}")
    print(f"Evidence Source : {note}")
    if r.matched_plan:
        print(f"Matched Plan    : {r.matched_plan}")
    if r.potential_difference is not None:
        print(f"Diff vs Nearest : ₹{r.potential_difference:+}")
    for tier, price, saving in r.cheaper_options:
        print(f"Cheaper Tier    : {tier} ₹{price:g} (would save ₹{saving:g})")
    print("=" * 77)

def run_vertical_slice():
    init_db()
    df = pd.read_csv("sample_statement.csv")
    df["cleaned"] = df["raw_description"].apply(clean_merchant_string)
    resolved = df["cleaned"].apply(resolve_merchant)
    df["normalized_merchant"] = resolved.apply(lambda t: t[0])
    source_by_merchant = dict(zip(df["normalized_merchant"], resolved.apply(lambda t: t[1])))

    candidates = analyze_recurring_patterns(df)
    print(f"Detected {len(candidates)} recurring charge(s).")

    for item in candidates:
        m = item["merchant"]
        print(f"\n{m}: ₹{item['user_amount']}/mo, recurring confidence {item['recurring_confidence']}%")

        if source_by_merchant.get(m) not in SEARCHABLE:
            print("  Recurring charge detected; service not identified locally, so no search was spent.")
            continue

        extracted, note = get_evidence(m)
        if extracted is None:
            print(f"  Recurring charge confirmed; price comparison unavailable ({note}).")
            continue

        report = validate_comparison(
            item["user_amount"], item["user_currency"], item["cadence"], extracted
        )
        print_drawer(item, report, note)

if __name__ == "__main__":
    run_vertical_slice()