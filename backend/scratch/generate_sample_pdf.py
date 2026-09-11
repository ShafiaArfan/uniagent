from pathlib import Path
from pypdf import PdfWriter


def generate_sample_pdf(output_path: Path) -> None:
    writer = PdfWriter()
    # Add two simple pages with placeholder text
    for i in range(2):
        # Create a blank page (size A4)
        writer.add_blank_page(width=595, height=842)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        writer.write(f)

if __name__ == "__main__":
    out = Path(__file__).resolve().parents[2] / "sample.pdf"
    generate_sample_pdf(out)
    print(f"Sample PDF created at {out}")
