from pathlib import Path

from statement_parser import parse_statement


def test_csv_parser_returns_canonical_columns():
    csv_path = Path("sample_statement.csv")

    df = parse_statement(csv_path)

    assert list(df.columns) == [
        "date",
        "amount",
        "currency",
        "raw_description",
    ]

    assert len(df) == 17
    assert df["currency"].eq("INR").all()
    assert df["amount"].notna().all()
    assert df["raw_description"].notna().all()