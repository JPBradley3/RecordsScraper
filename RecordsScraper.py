
from pathlib import Path
import re
import fitz  # PyMuPDF
import pandas as pd

SOURCE = Path("medical_records")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

# Strong document-type indicators, rather than diagnoses alone.
PATTERNS = {
    "Psychiatric evaluation": r"\bpsychiatric evaluation\b",
    "Psychological evaluation": r"\bpsychological evaluation\b",
    "Mental health assessment": r"\bmental health assessment\b",
    "Diagnostic assessment": r"\bdiagnostic assessment\b",
    "Psychiatric consultation": r"\bpsychiatric consult(?:ation)?\b",
    "Psychiatric intake": r"\bpsychiatric intake\b",
    "Mental status examination": r"\bmental status examination\b",
    "Psychosocial assessment": r"\bpsychosocial assessment\b",
    "Psychiatric history": r"\bpsychiatric history and examination\b",
    "Behavioral health evaluation": r"\bbehavioral health evaluation\b",
}

compiled = {
    label: re.compile(pattern, re.I)
    for label, pattern in PATTERNS.items()
}

records = []
selected = fitz.open()
seen_pages = set()

for path in sorted(SOURCE.rglob("*.pdf")):
    try:
        pdf = fitz.open(path)

        for i, page in enumerate(pdf):
            text = page.get_text("text")
            if not text.strip():
                continue

            matches = [
                label for label, pattern in compiled.items()
                if pattern.search(text)
            ]

            if not matches:
                continue

            records.append({
                "source_file": str(path),
                "original_page": i + 1,
                "document_types": "; ".join(matches),
                "matched_text": " | ".join(
                    line.strip()
                    for line in text.splitlines()
                    if any(
                        pattern.search(line)
                        for pattern in compiled.values()
                    )
                )[:1000],
            })

            # First pass: export only pages with matching headings.
            key = (str(path), i)
            if key not in seen_pages:
                selected.insert_pdf(
                    pdf, from_page=i, to_page=i
                )
                seen_pages.add(key)

        pdf.close()

    except Exception as exc:
        print(f"Could not process {path}: {exc}")

pd.DataFrame(records).to_csv(
    OUTPUT / "evaluation_candidates.csv", index=False
)

if len(selected):
    selected.save(OUTPUT / "evaluation_candidate_pages.pdf")

selected.close()

print(f"Found {len(records)} candidate pages.")
print(f"Results saved in: {OUTPUT.resolve()}")