from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd


REQUIRED_COLUMNS = {
    "date",
    "amount",
    "currency",
    "raw_description",
}


def parse_csv(source: str | Path | BinaryIO) -> pd.DataFrame:
    """
    Parse a ChargeLens CSV statement into the canonical transaction format.

    Expected columns:
        date, amount, currency, raw_description
    """
    df = pd.read_csv(source)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing)}"
        )

    return _normalize_dataframe(df)


def parse_pdf(source):
    import pdfplumber

    if isinstance(source, (str, Path)):
        pdf_source = source
    elif isinstance(source, bytes):
        pdf_source = BytesIO(source)
    else:
        pdf_source = source

    rows = []

    with pdfplumber.open(pdf_source) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                if not table:
                    continue

                rows.extend(_table_to_rows(table))

    if rows:
        df = pd.DataFrame(rows)
        return _normalize_dataframe(df)

    # Fall back to OCR when no transaction table could be extracted.
    return _parse_pdf_with_ocr(source)
def _parse_pdf_with_ocr(source):
    import pymupdf
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    if isinstance(source, (str, Path)):
        pdf_source = str(source)
    elif isinstance(source, bytes):
        pdf_source = source
    else:
        pdf_source = source.read()

    document = pymupdf.open(stream=pdf_source, filetype="pdf") if isinstance(
        pdf_source, (bytes, bytearray)
    ) else pymupdf.open(pdf_source)

    rows = []

    for page in document:
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
        image = Image.frombytes(
            "RGB",
            [pixmap.width, pixmap.height],
            pixmap.samples,
        )

        text = pytesseract.image_to_string(image)

        rows.extend(_ocr_text_to_rows(text))

    document.close()

    if not rows:
        raise ValueError(
            "No transaction table or OCR transaction rows could be extracted "
            "from the PDF."
        )

    df = pd.DataFrame(rows)
    return _normalize_dataframe(df)
def _ocr_text_to_rows(text):
    import re

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    dates = []
    descriptions = []
    amounts = []
    currencies = []

    for line in lines:
        # Ignore OCR'd column headers, including combined headers.
        if re.fullmatch(
            r"(date\s+description\s+amount|date\s+description\s+amount\s+currency)",
            line,
            re.IGNORECASE,
        ):
            continue

        date_match = re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2}", line)
        if date_match:
            dates.append(line)
            continue

        amount_match = re.fullmatch(r"[0-9,]+\.\d{2}", line)
        if amount_match:
            amounts.append(line.replace(",", ""))
            continue

        currency_match = re.fullmatch(
            r"(?:INR|NR|USD|EUR|GBP)",
            line,
            re.IGNORECASE,
        )
        if currency_match:
            currency = currency_match.group(0).upper()

            # OCR sometimes reads INR as NR.
            if currency == "NR":
                currency = "INR"

            currencies.append(currency)
            continue

        if line.lower() in {
            "date",
            "description",
            "amount",
            "currency",
        }:
            continue

        descriptions.append(line)

    row_count = min(
        len(dates),
        len(descriptions),
        len(amounts),
        len(currencies),
    )

    return [
        {
            "date": dates[index],
            "amount": amounts[index],
            "currency": currencies[index],
            "raw_description": descriptions[index],
        }
        for index in range(row_count)
    ]
def parse_statement(
    source: str | Path | bytes | BinaryIO,
    filename: str | None = None,
) -> pd.DataFrame:
    """
    Choose the local parser based on the statement file type.
    """
    name = (filename or str(source)).lower()

    if name.endswith(".csv"):
        return parse_csv(source)

    if name.endswith(".pdf"):
        return parse_pdf(source)

    raise ValueError(
        "Unsupported statement format. Please provide a CSV or PDF."
    )


def _table_to_rows(table: list[list[str | None]]) -> list[dict]:
    """
    Convert a PDF table into transaction dictionaries.

    This supports tables whose header contains the expected
    ChargeLens fields.
    """
    if not table:
        return []

    header = [
        str(cell or "").strip().lower().replace(" ", "_")
        for cell in table[0]
    ]

    aliases = {
    "description": "raw_description",
    "transaction_description": "raw_description",
    "merchant": "raw_description",
    "date": "date",
    "amount": "amount",
    "amount_(debit)": "amount",
    "debit": "amount",
    "currency": "currency",
    "raw_description": "raw_description",
}

    normalized_header = [
        aliases.get(column, column)
        for column in header
    ]

    required = {
        "date",
        "amount",
        "currency",
        "raw_description",
    }

    if not required.issubset(set(normalized_header)):
        return []

    rows = []

    for raw_row in table[1:]:
        if not raw_row:
            continue

        row = {}

        for index, value in enumerate(raw_row):
            if index >= len(normalized_header):
                continue

            column = normalized_header[index]

            if column in required:
                row[column] = (
                    str(value).strip()
                    if value is not None
                    else ""
                )

        if all(row.get(column) for column in required):
            rows.append(row)

    return rows


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize parser output without changing ChargeLens's
    existing downstream architecture.
    """
    df = df.copy()

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Parsed statement is missing required columns: "
            f"{sorted(missing)}"
        )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce",
    )

    df["currency"] = (
        df["currency"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["raw_description"] = (
        df["raw_description"]
        .astype(str)
        .str.strip()
    )

    df = df.dropna(
        subset=[
            "date",
            "amount",
        ]
    )

    df = df[
        [
            "date",
            "amount",
            "currency",
            "raw_description",
        ]
    ].reset_index(drop=True)

    return df