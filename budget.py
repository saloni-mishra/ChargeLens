import os
from datetime import datetime
from typing import Optional
from database import db

TOTAL_BUDGET = int(os.getenv("SERPAPI_TOTAL_BUDGET", "250"))
DEMO_RESERVE = int(os.getenv("SERPAPI_DEMO_RESERVE", "50"))

def check_budget_permission(bypass_reserve: bool = False) -> bool:
    month = datetime.now().strftime("%Y-%m")
    with db() as conn:
        row = conn.execute(
            "SELECT searches_used, billing_cycle_month FROM serpapi_budget WHERE id = 1"
        ).fetchone()
        used = row["searches_used"]
        if row["billing_cycle_month"] != month:
            conn.execute(
                "UPDATE serpapi_budget SET searches_used = 0, billing_cycle_month = ? WHERE id = 1",
                (month,),
            )
            used = 0
    return (TOTAL_BUDGET - used) > (0 if bypass_reserve else DEMO_RESERVE)

def log_audit_event(search_type: str, query: str, status: str,
                    http_code: Optional[int] = None, error: Optional[str] = None):
    with db() as conn:
        conn.execute(
            "INSERT INTO serpapi_audit_log "
            "(search_type, query, status, http_code, error_message, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (search_type, query, status, http_code, error, datetime.now().isoformat()),
        )

def record_search_success(search_type: str, query: str, http_code: int = 200):
    with db() as conn:
        conn.execute("UPDATE serpapi_budget SET searches_used = searches_used + 1 WHERE id = 1")
    log_audit_event(search_type, query, "SUCCESS", http_code)