import re
import pytest
import database
import search

class FakeResponse:
    status_code = 200
    text = ""
    def json(self):
        return {"organic_results": []}

def test_search_query_contains_no_financial_data(monkeypatch, tmp_path):
    # Set up isolated SQLite db and replay directory
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    database.init_db()
    monkeypatch.setattr(search, "REPLAY_DIR", tmp_path / "replay")
    monkeypatch.setattr(search, "SERPAPI_KEY", "test-key")

    sent_requests = []
    def fake_get(url, params=None, timeout=None):
        sent_requests.append(params)
        return FakeResponse()
    monkeypatch.setattr(search.requests, "get", fake_get)

    search.fetch_pricing_evidence("Netflix")

    assert len(sent_requests) == 1
    query = sent_requests[0]["q"]
    
    # Assertions guaranteeing data privacy:
    assert not re.search(r"\d", query), "Leak detected: Digits found in search query!"
    assert "@" not in query and "UPI" not in query, "Leak detected: UPI or raw tokens in query!"
    assert set(sent_requests[0].keys()) == {"engine", "q", "gl", "hl", "num", "api_key"}