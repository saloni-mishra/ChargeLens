import re
from functools import lru_cache
from typing import Tuple
from database import db

LOCAL_KNOWLEDGE = [
    (r"\bNETFLIX", "Netflix"),
    (r"\bSPOTIFY", "Spotify"),
    (r"\bAMAZON\s*PRIME|\bAMZN\s*PRIME|\bPRIME\s*VIDEO", "Amazon Prime"),
    (r"\bJIO\s*HOTSTAR|\bHOTSTAR|\bNOVI\s*DIGITAL", "JioHotstar"),
    (r"\bYOUTUBE", "YouTube Premium"),
    (r"\bADOBE", "Adobe"),
    (r"\bCANVA", "Canva"),
    (r"\bCHATGPT|\bOPENAI", "OpenAI ChatGPT"),
]
_RULES = [(re.compile(p, re.I), name) for p, name in LOCAL_KNOWLEDGE]

@lru_cache(maxsize=None)
def resolve_merchant(cleaned_name: str) -> Tuple[str, str]:
    """Returns (canonical_name, source). Never spends an API credit."""
    for rx, canonical in _RULES:
        if rx.search(cleaned_name):
            return canonical, "LOCAL_RULE"
            
    with db() as conn:
        row = conn.execute(
            "SELECT canonical_name FROM identity_cache WHERE raw_token = ?",
            (cleaned_name,),
        ).fetchone()
    if row:
        return row["canonical_name"], "IDENTITY_CACHE"
        
    return cleaned_name, "UNRESOLVED"