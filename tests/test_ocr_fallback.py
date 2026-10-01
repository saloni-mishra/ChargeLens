from pathlib import Path

from statement_parser import parse_statement


def test_pdf_ocr_fallback_returns_transactions():
    pdf_path = Path("tests/fixtures/sample_ocr.pdf")

    df = parse_statement(pdf_path)

    assert list(df.columns) == [
        "date",
        "amount",
        "currency",
        "raw_description",
    ]
    assert len(df) == 4
    assert df["currency"].eq("INR").all()
    assert df["amount"].notna().all()
    assert df["raw_description"].notna().all()