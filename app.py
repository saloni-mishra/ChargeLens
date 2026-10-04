import io
import os

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from statement_parser import parse_statement
from database import init_db
from cleaner import clean_merchant_string
from normalizer import resolve_merchant
from detector import analyze_recurring_patterns
from slice_runner import get_evidence, SEARCHABLE
from validator import validate_comparison
import budget


load_dotenv()

app = FastAPI(title="ChargeLens Core API")

init_db()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_index():
    return FileResponse("static/index.html")


@app.get("/api/budget")
def read_budget():
    with budget.db() as conn:
        row = conn.execute(
            "SELECT searches_used FROM serpapi_budget WHERE id = 1"
        ).fetchone()

        used = row["searches_used"] if row else 0

    return {
        "used": used,
        "total": budget.TOTAL_BUDGET,
        "demo_reserve": budget.DEMO_RESERVE,
    }

def _load_statement_dataframe(filename: str, contents: bytes) -> pd.DataFrame:
    suffix = os.path.splitext(filename.lower())[1]

    if suffix == ".csv":
        try:
            df = pd.read_csv(
                io.StringIO(contents.decode("utf-8-sig"))
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to read CSV statement: {exc}",
            )

    elif suffix == ".pdf":
        temp_path = f"_chargelens_upload_{os.getpid()}.pdf"

        try:
            with open(temp_path, "wb") as temp_file:
                temp_file.write(contents)

            rows = parse_statement(temp_path)
            df = pd.DataFrame(rows)

        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse PDF statement: {exc}",
            )

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a CSV or PDF statement.",
        )

    required_cols = {
        "date",
        "amount",
        "currency",
        "raw_description",
    }

    missing = required_cols - set(df.columns)

    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Statement is missing required columns: "
                f"{sorted(missing)}"
            ),
        )

    return df

@app.post("/api/analyze")
async def analyze_statement(file: UploadFile = File(...)):
    try:
        contents = await file.read()

        df = _load_statement_dataframe(
            file.filename or "",
            contents,
        )

        df["cleaned"] = df["raw_description"].apply(
            clean_merchant_string
        )

        resolved = df["cleaned"].apply(resolve_merchant)

        df["normalized_merchant"] = resolved.apply(
            lambda result: result[0]
        )

        source_by_merchant = dict(
            zip(
                df["normalized_merchant"],
                resolved.apply(lambda result: result[1]),
            )
        )

        candidates = analyze_recurring_patterns(df)

        results = []

        for item in candidates:
            merchant = item["merchant"]
            source = source_by_merchant.get(merchant)

            base_result = {
                **item,
                "search_performed": False,
                "price_extracted": False,
                "confidence_tier": "UNAVAILABLE",
                "decision_reason": "Pricing evidence unavailable.",
                "matched_plan": None,
                "potential_difference": None,
                "cheaper_options": [],
                "provenance": {
                    "source": None,
                    "query": None,
                    "retrieved_at": None,
                    "extraction_model": os.getenv(
                        "GEMINI_MODEL",
                        "gemini-2.5-flash",
                    ),
                    "validation_method": (
                        "Deterministic Python validator"
                    ),
                },
            }

            if source not in SEARCHABLE:
                base_result["decision_reason"] = (
                    "Recurring charge detected, but the service "
                    "could not be resolved locally."
                )
                results.append(base_result)
                continue

            extracted, note, provenance = get_evidence(merchant)

            base_result["evidence_note"] = note
            base_result["provenance"] = provenance

            if extracted is None:
                base_result["decision_reason"] = (
                    f"Recurring charge confirmed; "
                    f"price comparison unavailable ({note})."
                )
                results.append(base_result)
                continue

            report = validate_comparison(
                item["user_amount"],
                item["user_currency"],
                item["cadence"],
                extracted,
            )

            base_result.update(
                {
                    "search_performed": report.search_performed,
                    "price_extracted": report.price_extracted,
                    "confidence_tier": report.confidence_tier,
                    "decision_reason": report.decision_reason,
                    "matched_plan": report.matched_plan,
                    "potential_difference": report.potential_difference,
                    "cheaper_options": [
                        {
                            "tier": option[0],
                            "price": option[1],
                            "saving": option[2],
                            "eligibility": option[3],
                        }
                        for option in report.cheaper_options
                    ],
                }
            )

            results.append(base_result)

        return {
            "filename": file.filename,
            "transactions": len(df),
            "recurring_count": len(results),
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {exc}",
        )