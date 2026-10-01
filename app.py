import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from database import init_db
from cleaner import clean_merchant_string
from normalizer import resolve_merchant
from detector import analyze_recurring_patterns
from slice_runner import get_evidence, SEARCHABLE
from validator import validate_comparison
import budget

app = FastAPI(title="StatementIQ Core API")

# Initialize database tables on startup
init_db()

# Mount frontend assets
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

@app.get("/api/budget")
def read_budget():
    with budget.db() as conn:
        row = conn.execute("SELECT searches_used FROM serpapi_budget WHERE id = 1").fetchone()
        used = row["searches_used"] if row else 0
    return {
        "used": used,
        "total": budget.TOTAL_BUDGET,
        "demo_reserve": budget.DEMO_RESERVE
    }

@app.post("/api/analyze")
async def analyze_statement(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV statement: {str(e)}")

    required_cols = {"date", "amount", "currency", "raw_description"}
    if not required_cols.issubset(df.columns):
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns. Expected: {list(required_cols)}"
        )

    # 1. Clean and normalize merchants locally
    df["cleaned"] = df["raw_description"].apply(clean_merchant_string)
    resolved = df["cleaned"].apply(resolve_merchant)
    df["normalized_merchant"] = resolved.apply(lambda t: t[0])
    source_by_merchant = dict(zip(df["normalized_merchant"], resolved.apply(lambda t: t[1])))

    # 2. Local recurring charge detection
    candidates = analyze_recurring_patterns(df)
    results = []

    # 3. Market price verification stage
    for item in candidates:
        m = item["merchant"]
        
        # Branch 1: Unresolved locally -> Search intentionally skipped to guard quota
        if source_by_merchant.get(m) not in SEARCHABLE:
            item["report"] = {
                "confidence_tier": "UNAVAILABLE",
                "reason_code": "IDENTITY_UNVERIFIED",
                "decision_reason": "Recurring pattern detected, but service identity is unverified locally.",
                "currency_checked": False,
                "currency_match": False,
                "cadence_checked": False,
                "cadence_match": False,
                "matched_plan": None,
                "potential_difference": None,
                "cheaper_options": []
            }
            item["evidence_note"] = "Local Decision: Service identity unverified. External search skipped to preserve budget."
            results.append(item)
            continue

        # Branch 2: Search attempted but throttled or network issue
        extracted, note = get_evidence(m)
        if extracted is None:
            item["report"] = {
                "confidence_tier": "UNAVAILABLE",
                "reason_code": "SEARCH_THROTTLED",
                "decision_reason": f"Recurring charge confirmed; public pricing unavailable ({note}).",
                "currency_checked": False,
                "currency_match": False,
                "cadence_checked": False,
                "cadence_match": False,
                "matched_plan": None,
                "potential_difference": None,
                "cheaper_options": []
            }
            item["evidence_note"] = f"Search Guard Notice: {note}"
            results.append(item)
            continue

        # Branch 3: Search succeeded -> Run Validator
        report = validate_comparison(
            user_amount=item["user_amount"],
            user_currency=item["user_currency"],
            user_cadence=item["cadence"],
            extracted=extracted
        )

        item["report"] = {
            "confidence_tier": report.confidence_tier,
            "reason_code": report.reason_code,
            "decision_reason": report.decision_reason,
            "currency_checked": report.currency_checked,
            "currency_match": report.currency_match,
            "cadence_checked": report.cadence_checked,
            "cadence_match": report.cadence_match,
            "matched_plan": report.matched_plan,
            "potential_difference": report.potential_difference,
            "cheaper_options": report.cheaper_options
        }
        item["evidence_note"] = note
        results.append(item)

    return {"results": results}