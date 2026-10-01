import os
import json
import hashlib
import requests
from pathlib import Path
from typing import Optional, Tuple
from budget import check_budget_permission, record_search_success, log_audit_event

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
REPLAY_DIR = Path("serp_replay")
USE_REPLAY = os.getenv("STATEMENTIQ_REPLAY", "1") == "1"
DEMO_MODE = os.getenv("STATEMENTIQ_DEMO", "0") == "1"

def build_query(service: str) -> str:
    # Zero private user data leaked
    return f"{service} subscription plans India monthly price official"

def _trim(data: dict) -> Tuple[str, Optional[str]]:
    parts = []
    url = None
    box = data.get("answer_box") or {}
    text = box.get("snippet") or box.get("answer")
    if text:
        parts.append(f"Direct Answer: {text}")
        url = box.get("link")
        
    for item in data.get("organic_results", [])[:3]:
        url = url or item.get("link")
        parts.append(f"{item.get('title', '')} | {item.get('snippet', '')}")
        
    return "\n".join(parts)[:900], url

def fetch_pricing_evidence(service: str):
    """Returns (query, snippets, source_url, status)."""
    query = build_query(service)
    replay = REPLAY_DIR / (hashlib.md5(query.encode()).hexdigest() + ".json")

    if USE_REPLAY and replay.exists():
        snippets, url = _trim(json.loads(replay.read_text()))
        return query, snippets, url, "REPLAY"

    if not SERPAPI_KEY:
        return query, None, None, "NO_API_KEY"

    if not check_budget_permission(bypass_reserve=DEMO_MODE):
        log_audit_event("PRICING_SEARCH", query, "THROTTLED")
        return query, None, None, "BUDGET_THROTTLED"

    params = {
        "engine": "google",
        "q": query,
        "gl": "in",
        "hl": "en",
        "num": 4,
        "api_key": SERPAPI_KEY
    }

    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=12)
    except requests.RequestException as e:
        log_audit_event("PRICING_SEARCH", query, "FAILED", 0, str(e))
        return query, None, None, "NETWORK_ERROR"

    data = resp.json() if resp.status_code == 200 else {}
    if resp.status_code != 200 or data.get("error"):
        log_audit_event("PRICING_SEARCH", query, "FAILED", resp.status_code, resp.text[:200])
        return query, None, None, "NETWORK_ERROR"

    REPLAY_DIR.mkdir(exist_ok=True)
    replay.write_text(json.dumps(data))
    record_search_success("PRICING_SEARCH", query, resp.status_code)
    snippets, url = _trim(data)
    return query, snippets, url, "LIVE_SERPAPI"