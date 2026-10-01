from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTPUT = Path(__file__).parent / "sample_ocr.pdf"

ROWS = [
    ("2026-04-05", "UPI-NETFLIX.COM*INDIA", "649.00", "INR"),
    ("2026-04-10", "UPI-SPOTIFY-INDIA-PAYU", "119.00", "INR"),
    ("2026-04-12", "SWIGGY BANGALORE", "450.00", "INR"),
    ("2026-04-15", "CULT FIT MEMBERSHIP", "1499.00", "INR"),
]


def main():
    width = 1800
    height = 900

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype(
        r"C:\Windows\Fonts\arial.ttf",
        38,
    )

    y = 80

    draw.text(
        (80, y),
        "Date        Description                         Amount     Currency",
        fill="black",
        font=font,
    )

    y += 80

    for date, description, amount, currency in ROWS:
        line = (
            f"{date}   "
            f"{description:<35} "
            f"{amount:>10}   "
            f"{currency}"
        )

        draw.text(
            (80, y),
            line,
            fill="black",
            font=font,
        )

        y += 90

    image.save(
        OUTPUT,
        "PDF",
        resolution=200.0,
    )

    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()