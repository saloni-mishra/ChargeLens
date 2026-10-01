from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


OUTPUT = Path(__file__).parent / "sample.pdf"


def generate_pdf(output_filename=OUTPUT):
    output_filename = Path(output_filename)
    output_filename.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_filename),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "BankTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
    )

    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#64748b"),
        leading=13,
    )

    cell_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    cell_bold_style = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    elements = []

    elements.append(
        Paragraph("APEX BANK OF INDIA", title_style)
    )

    elements.append(
        Paragraph(
            "Account Statement | Savings Account: "
            "<b>XXXX-XXXX-4912</b>",
            meta_style,
        )
    )

    elements.append(
        Paragraph(
            "Customer Name: <b>Rohan Sharma</b> | "
            "Statement Period: <b>01-Apr-2026 to 15-Jul-2026</b>",
            meta_style,
        )
    )

    elements.append(Spacer(1, 16))

    summary_data = [
        [
            "Opening Balance",
            "Total Debits",
            "Total Credits",
            "Closing Balance",
        ],
        [
            "INR 84,250.00",
            "INR 18,410.00",
            "INR 65,000.00",
            "INR 1,30,840.00",
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[130, 130, 130, 150],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#f8fafc"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#64748b"),
                ),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#e2e8f0"),
                ),
            ]
        )
    )

    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    raw_transactions = [
        (
            "2026-04-05",
            "UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm",
            "UPI",
            "649.00",
            "INR",
        ),
        (
            "2026-04-10",
            "UPI-SPOTIFY-INDIA-PAYU@axisbank",
            "UPI",
            "119.00",
            "INR",
        ),
        (
            "2026-04-12",
            "SWIGGY BANGALORE IN ORDER 8812",
            "POS",
            "450.00",
            "INR",
        ),
        (
            "2026-04-15",
            "CULT FIT MEMBERSHIP BANGALORE",
            "ACH",
            "1499.00",
            "INR",
        ),
        (
            "2026-04-18",
            "UBER INDIA BANGALORE TRIP-912",
            "POS",
            "220.00",
            "INR",
        ),
        (
            "2026-05-02",
            "ZOMATO GURGAON RESTAURANT BILL",
            "UPI",
            "380.00",
            "INR",
        ),
        (
            "2026-05-04",
            "POS 416021XXXXXX1029 NETFLIX ENTERTAINMENT",
            "POS",
            "649.00",
            "INR",
        ),
        (
            "2026-05-11",
            "POS 552140XXXXXX8812 SPOTIFY INDIA BANGALORE",
            "POS",
            "119.00",
            "INR",
        ),
        (
            "2026-05-15",
            "ELECTRICITY BILL DESK MUMBAI",
            "BIL",
            "1200.00",
            "INR",
        ),
        (
            "2026-05-16",
            "CULT FITNESS RECURRING GYM DEBIT",
            "ACH",
            "1499.00",
            "INR",
        ),
        (
            "2026-06-01",
            "SWIGGY BANGALORE IN ORDER 4410",
            "POS",
            "540.00",
            "INR",
        ),
        (
            "2026-06-05",
            "ACH D- NETFLIX INDIA 000123984",
            "ACH",
            "649.00",
            "INR",
        ),
        (
            "2026-06-09",
            "UPI-SPOTIFY-RECURRING@paytm",
            "UPI",
            "119.00",
            "INR",
        ),
        (
            "2026-06-15",
            "CULT FIT MONTHLY GYM BANGALORE",
            "ACH",
            "1499.00",
            "INR",
        ),
        (
            "2026-07-05",
            "UPI-NETFLIX.COM*5512-paytm@paytm",
            "UPI",
            "649.00",
            "INR",
        ),
    ]

    table_data = [
        [
            Paragraph("<b>Date</b>", cell_bold_style),
            Paragraph(
                "<b>Transaction Description</b>",
                cell_bold_style,
            ),
            Paragraph("<b>Channel</b>", cell_bold_style),
            Paragraph("<b>Amount (Debit)</b>", cell_bold_style),
            Paragraph("<b>Currency</b>", cell_bold_style),
        ]
    ]

    for date, desc, channel, amount, currency in raw_transactions:
        table_data.append(
            [
                Paragraph(date, cell_style),
                Paragraph(desc, cell_style),
                Paragraph(channel, cell_style),
                Paragraph(amount, cell_style),
                Paragraph(currency, cell_style),
            ]
        )

    transaction_table = Table(
        table_data,
        colWidths=[65, 275, 55, 85, 60],
    )

    transaction_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#0f172a"),
                ),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#f8fafc"),
                    ],
                ),
            ]
        )
    )

    elements.append(transaction_table)
    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(
            "<i>* This document is generated for demonstration and "
            "testing purposes. All personal information and card "
            "references are synthetic.</i>",
            meta_style,
        )
    )

    doc.build(elements)

    print(f"Successfully generated: {output_filename}")


if __name__ == "__main__":
    generate_pdf()