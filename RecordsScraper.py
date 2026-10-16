from pathlib import Path
import re
import fitz  # PyMuPDF
import pandas as pd

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SOURCE = Path("medical_records")
OUTPUT = Path("output")
OUTPUT.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# DOCUMENT TYPES TO SEARCH FOR
# --------------------------------------------------

PATTERNS = {
    "Psychiatric evaluation":
        r"\bpsychiatric evaluation\b",

    "Psychological evaluation":
        r"\bpsychological evaluation\b",

    "Mental health assessment":
        r"\bmental health assessment\b",

    "Diagnostic assessment":
        r"\bdiagnostic assessment\b",

    "Psychiatric consultation":
        r"\bpsychiatric consult(?:ation)?\b",

    "Psychiatric intake":
        r"\bpsychiatric intake\b",

    "Mental status examination":
        r"\bmental status examination\b",

    "Psychosocial assessment":
        r"\bpsychosocial assessment\b",

    "Psychiatric history":
        r"\bpsychiatric history and examination\b",

    "Behavioral health evaluation":
        r"\bbehavioral health evaluation\b",

    # Psychiatric Emergency Services (PES)
    "Psychiatric Emergency Services":
        r"\bpsychiatric emergency services\b",

    "Psychiatric Emergency Service":
        r"\bpsychiatric emergency service\b",

    "PES abbreviation":
        r"\bPES\b",

    "Psychiatric emergency evaluation":
        r"\bpsychiatric emergency evaluation\b",

    "Psychiatric emergency assessment":
        r"\bpsychiatric emergency assessment\b",

    "Emergency psychiatric evaluation":
        r"\bemergency psychiatric evaluation\b",

    "Emergency mental health evaluation":
        r"\bemergency mental health evaluation\b",

    # Additional relevant emergency documentation
    "Psychiatric crisis evaluation":
        r"\bpsychiatric crisis evaluation\b",

    "Crisis assessment":
        r"\bcrisis assessment\b",

    "Suicide risk assessment":
        r"\bsuicide risk assessment\b",

    "Psychiatric discharge summary":
        r"\bpsychiatric discharge summary\b",

    "Mental health discharge summary":
        r"\bmental health discharge summary\b",

    "Psychiatric admission assessment":
        r"\bpsychiatric admission assessment\b",

    "Psychiatric consult note":
        r"\bpsychiatric consult note\b",
}

COMPILED_PATTERNS = {
    label: re.compile(pattern, re.IGNORECASE)
    for label, pattern in PATTERNS.items()
}

# --------------------------------------------------
# INITIALIZE OUTPUTS
# --------------------------------------------------

records = []
selected_pages = fitz.open()

# Prevent duplicate insertion of the same source page.
seen_pages = set()

# --------------------------------------------------
# PROCESS ALL PDF FILES
# --------------------------------------------------

pdf_files = sorted(SOURCE.rglob("*.pdf"))

if not pdf_files:
    print(f"No PDF files found in: {SOURCE.resolve()}")

for path in pdf_files:
    print(f"Processing: {path}")

    try:
        with fitz.open(path) as pdf:

            for page_index, page in enumerate(pdf):
                text = page.get_text("text")

                # Skip pages with no extractable text.
                if not text.strip():
                    continue

                # Find every matching document type.
                matches = [
                    label
                    for label, pattern
                    in COMPILED_PATTERNS.items()
                    if pattern.search(text)
                ]

                if not matches:
                    continue

                # Record lines containing matching phrases.
                matched_lines = []

                for line in text.splitlines():
                    line = line.strip()

                    if not line:
                        continue

                    if any(
                        pattern.search(line)
                        for pattern in COMPILED_PATTERNS.values()
                    ):
                        matched_lines.append(line)

                # Add the page to the index.
                records.append({
                    "source_file": str(path),
                    "original_page": page_index + 1,
                    "document_types": "; ".join(matches),
                    "matched_text": " | ".join(
                        matched_lines
                    )[:1000],
                })

                # Copy the matching page to the output PDF.
                page_key = (str(path.resolve()), page_index)

                if page_key not in seen_pages:
                    selected_pages.insert_pdf(
                        pdf,
                        from_page=page_index,
                        to_page=page_index,
                    )
                    seen_pages.add(page_key)

    except Exception as exc:
        print(f"ERROR processing {path}: {exc}")

# --------------------------------------------------
# SAVE CSV INDEX
# --------------------------------------------------

csv_path = OUTPUT / "evaluation_candidates.csv"

columns = [
    "source_file",
    "original_page",
    "document_types",
    "matched_text",
]

df = pd.DataFrame(records, columns=columns)

df.to_csv(csv_path, index=False, encoding="utf-8-sig")

# --------------------------------------------------
# SAVE MATCHING PAGES AS A PDF
# --------------------------------------------------

pdf_path = OUTPUT / "evaluation_candidate_pages.pdf"

if len(selected_pages) > 0:
    selected_pages.save(pdf_path, garbage=4, deflate=True)
    print(f"Candidate PDF saved: {pdf_path.resolve()}")
else:
    print("No matching pages found; no candidate PDF created.")

selected_pages.close()

# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

print("\nProcessing complete.")
print(f"PDF files examined: {len(pdf_files)}")
print(f"Matching pages: {len(records)}")
print(f"CSV index: {csv_path.resolve()}")

if len(records):
    print("\nMatches by document type:")

    counts = (
        df["document_types"]
        .str.split("; ")
        .explode()
        .value_counts()
    )

    for document_type, count in counts.items():
        print(f"  {document_type}: {count}")
