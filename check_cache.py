import sqlite3

c = sqlite3.connect("ChargeLens.db")

rows = c.execute("""
SELECT canonical_name, extracted_json
FROM pricing_cache
WHERE canonical_name IN ("Netflix", "Spotify", "YouTube Premium")
""").fetchall()

for row in rows:
    print(row)
