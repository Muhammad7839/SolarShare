"""Extract a concise text summary from a PDF for product and investor review workflows."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _extract_with_pypdf(path: Path, max_pages: int, max_chars: int) -> str | None:
    """Extract text using pypdf when the package is available."""
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return None

    reader = PdfReader(str(path))
    parts = [f"pages={len(reader.pages)}"]
    for index, page in enumerate(reader.pages[:max_pages]):
        text = (page.extract_text() or "").strip()
        parts.append(f"\n--- page {index + 1} ---\n{text[:max_chars]}")
    return "\n".join(parts).strip()


def _extract_with_pdftotext(path: Path, max_chars: int) -> str | None:
    """Extract text using pdftotext when available."""
    if shutil.which("pdftotext") is None:
        return None

    process = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        return None

    text = process.stdout.strip()
    if not text:
        return ""
    return text[:max_chars]


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract quick PDF summary text.")
    parser.add_argument("pdf_path", help="Path to a local PDF file")
    parser.add_argument("--max-pages", type=int, default=3, help="Pages to read with pypdf")
    parser.add_argument("--max-chars", type=int, default=2200, help="Maximum output characters")
    args = parser.parse_args()

    path = Path(args.pdf_path).expanduser().resolve()
    if not path.exists() or path.suffix.lower() != ".pdf":
        print("Invalid PDF path.", file=sys.stderr)
        return 1

    summary = _extract_with_pypdf(path, max_pages=args.max_pages, max_chars=args.max_chars)
    if summary is None:
        summary = _extract_with_pdftotext(path, max_chars=args.max_chars)

    if summary is None:
        print(
            "No PDF extractor available. Install pypdf (`python3 -m pip install pypdf`) "
            "or poppler (`brew install poppler`).",
            file=sys.stderr,
        )
        return 2

    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
