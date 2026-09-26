import os
import re
import pdfplumber
from supabase import Client, create_client

# 1. SUPABASE CREDENTIALS
# (Aapke project settings se URL aur ANON KEY)
SUPABASE_URL = "https://ygboaajfqrryditrgzhu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlnYm9hYWpmcXJyeWRpdHJnemh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMDMxOTgsImV4cCI6MjEwNTY3OTE5OH0.prXkOtFTFgYnRhREh2wykEyCIgpo-nj55o8kzCekvWo"  # Yahan apni anon public key paste karein

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Advocate ID jo abhi mili
ADVOCATE_ID = "75423310-4f1b-472a-92b9-17ddbafda3df"


def parse_cause_list(pdf_path, target_cases):
    """Calcutta High Court Cause List PDF se cases search karta hai."""
    results = {}
    current_court = "Unknown"
    court_sitting_notes = {}

    print(f"Scanning PDF for {len(target_cases)} cases...")

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            court_match = re.search(r"COURT NO\.?\s*(\d+)", text, re.IGNORECASE)
            if court_match:
                current_court = court_match.group(1)

            if (
                "will not be sitting" in text.lower()
                or "will not sit" in text.lower()
            ):
                court_sitting_notes[current_court] = "Court Not Sitting / Leave"

            for case in target_cases:
                if case in text and case not in results:
                    lines = text.split("\n")
                    item_no = None

                    for line_idx, line in enumerate(lines):
                        if case in line:
                            item_match = re.search(r"^\s*(\d{1,4})\b", line)
                            if not item_match and line_idx > 0:
                                item_match = re.search(
                                    r"^\s*(\d{1,4})\b", lines[line_idx - 1]
                                )

                            if item_match:
                                item_no = int(item_match.group(1))

                            results[case] = {
                                "advocate_id": ADVOCATE_ID,
                                "advocate_name": "Advocate Vivek",
                                "case_number": case,
                                "court_room": current_court,
                                "target_item": item_no,
                                "bench_status": court_sitting_notes.get(
                                    current_court, "Sitting"
                                ),
                                "hearing_date": "2026-09-22",
                            }

    return results


def sync_to_supabase(parsed_cases):
    """Parsed cases ko Supabase mein push karta hai."""
    if not parsed_cases:
        print("No cases to push.")
        return

    print(f"\nPushing {len(parsed_cases)} cases to Supabase...")
    for case_no, data in parsed_cases.items():
        try:
            # Insert case
            response = supabase.table("cases").insert(data).execute()
            print(
                f" Saved: {case_no} -> Court {data['court_room']} | Item {data['target_item']}"
            )
        except Exception as e:
            print(f"❌ Error inserting {case_no}: {e}")


if __name__ == "__main__":
    cases_from_sarthak = [
        "WPA/16201/2017",
        "WPA/22897/2019",
        "WPA/11035/2026",
        "WPA/20292/2026",
    ]

    pdf_file = "clause_list.pdf"

    # Step A: Parse PDF
    matched_data = parse_cause_list(pdf_file, cases_from_sarthak)

    # Step B: Push to Database
    sync_to_supabase(matched_data)