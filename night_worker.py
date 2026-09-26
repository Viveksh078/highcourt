import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from curl_cffi import requests
import pdfplumber
from supabase import create_client, Client

# --- Configurations ---
SUPABASE_URL = "https://ygboaajfqrryditrgzhu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlnYm9hYWpmcXJyeWRpdHJnemh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMDMxOTgsImV4cCI6MjEwNTY3OTE5OH0.prXkOtFTFgYnRhREh2wykEyCIgpo-nj55o8kzCekvWo"
ADVOCATE_ID = "75423310-4f1b-472a-92b9-17ddbafda3df"
ADVOCATE_NAME = "Sarthak"

# Telegram Bot Config
TELEGRAM_BOT_TOKEN = "8892593538:AAEFB8hEyPI5612KC7iSVfrPKRp-IWmyhTs"  # <-- day_tracker wala Bot Token yahan daalein
TELEGRAM_CHAT_ID = "5834882829"                # <-- Advocate Telegram Chat ID

NOTICES_URL = "https://www.calcuttahighcourt.gov.in/Notices"
BASE_DOMAIN = "https://www.calcuttahighcourt.gov.in"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def send_night_summary_telegram(matched_cases, hearing_date):
    """Raat ko hi advocate ko kal ke listed cases ka clean schedule bhejta hai."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("⚠️ Telegram token not configured, skipping night alert.")
        return

    lines = [
        f"📋 <b>High Court Schedule for {hearing_date}</b>\n",
        f"Advocate: <b>{ADVOCATE_NAME}</b>\n",
        f"Total Listed Cases: <b>{len(matched_cases)}</b>\n",
        "────────────────────────"
    ]

    for case_no, info in matched_cases.items():
        lines.append(
            f"⚖️ <code>{case_no}</code>\n"
            f"   🏛️ Court Room: <b>{info['court_room']}</b> | 🔢 Item: <b>{info['target_item']}</b>\n"
        )

    lines.append("────────────────────────")
    lines.append("🔔 <i>MunshiAI will track these courts live tomorrow morning.</i>")

    message_text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML"
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("📲 Nightly Telegram summary sent to advocate successfully!")
        else:
            print(f"⚠️ Telegram send error: {r.text}")
    except Exception as e:
        print(f"⚠️ Telegram network error: {e}")


def fetch_latest_cause_list(save_path="clause_list.pdf"):
    if os.path.exists(save_path) and os.path.getsize(save_path) > 500 * 1024:
        size_mb = round(os.path.getsize(save_path) / (1024 * 1024), 2)
        print(f"📁 Local full cause list found ({size_mb} MB). Skipping re-download.")
        return save_path

    print("🌐 [1/3] Fetching latest Cause List PDF from High Court portal...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(NOTICES_URL, impersonate="chrome120", headers=headers, timeout=25, verify=False)
        target_link = None
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                text = a_tag.get_text(strip=True).lower()
                if "Notice-Files/CL/" in href or ("cause" in text and "appellate" in text):
                    target_link = href if href.startswith("http") else f"{BASE_DOMAIN}/{href.lstrip('/')}"
                    print(f"🎯 Found list notice: {a_tag.get_text(strip=True)[:60]}...")
                    break

        if not target_link:
            return save_path if os.path.exists(save_path) else None

        pdf_resp = requests.get(target_link, impersonate="chrome120", headers=headers, timeout=120, verify=False)
        if pdf_resp.status_code == 200 and pdf_resp.content.startswith(b"%PDF"):
            with open(save_path, "wb") as f:
                f.write(pdf_resp.content)
            print(f"✅ PDF downloaded successfully ({len(pdf_resp.content) // 1024} KB)")
            return save_path
        else:
            return save_path if os.path.exists(save_path) else None

    except Exception as e:
        print(f"⚠️ Fetch warning: {e}")
        return save_path if os.path.exists(save_path) else None


def get_all_monitored_cases():
    """Option 1: Database ke Master Vault se advocate ke saare saved cases fetch karta hai."""
    try:
        res = supabase.table("cases").select("case_number").eq("advocate_id", ADVOCATE_ID).execute()
        if res.data:
            cases = [row["case_number"] for row in res.data]
            return list(set(cases))
    except Exception as e:
        print(f"⚠️ Warning fetching cases from DB: {e}")
    return []


def parse_cause_list(pdf_path, target_cases):
    print(f"📄 [2/3] Scanning PDF against {len(target_cases)} monitored cases...")
    results = {}
    current_court = "Unknown"
    
    court_pattern = re.compile(r"COURT\s+NO\.\s*(\d+)", re.IGNORECASE)
    item_pattern = re.compile(r"^(\d+)\s+([A-Z]+/\d+/\d{4})", re.IGNORECASE | re.MULTILINE)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"   Scanning {total_pages} pages in cause list...")
        
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            court_match = court_pattern.search(text)
            if court_match:
                current_court = court_match.group(1)
            
            matches = item_pattern.findall(text)
            for item_no, case_no in matches:
                case_clean = case_no.upper().replace(" ", "")
                for target in target_cases:
                    target_clean = target.upper().replace(" ", "")
                    if target_clean in case_clean:
                        results[target_clean] = {
                            "court_room": current_court,
                            "target_item": int(item_no),
                            "case_number": target_clean
                        }
                        print(f"   🎯 MATCH: {target_clean} -> Court {current_court} | Item {item_no}")
                        
    return results


def sync_to_supabase(matched_cases):
    print(f"💾 [3/3] Syncing {len(matched_cases)} cases into Supabase...")
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    for case_no, data in matched_cases.items():
        payload = {
            "advocate_id": ADVOCATE_ID,
            "advocate_name": ADVOCATE_NAME,
            "case_number": data["case_number"],
            "court_room": str(data["court_room"]),
            "target_item": data["target_item"],
            "bench_status": "Scheduled",
            "hearing_date": today_date
        }
        try:
            existing = supabase.table("cases").select("id").eq("advocate_id", ADVOCATE_ID).eq("case_number", data["case_number"]).execute()
            if existing.data:
                supabase.table("cases").update(payload).eq("id", existing.data[0]["id"]).execute()
                print(f"   🔄 Updated: {case_no} -> Court {data['court_room']} | Item {data['target_item']}")
            else:
                supabase.table("cases").insert(payload).execute()
                print(f"   ✅ Inserted: {case_no} -> Court {data['court_room']} | Item {data['target_item']}")
        except Exception as e:
            print(f"   ❌ Error saving {case_no}: {e}")


def run_night_pipeline():
    # 1. Database se saare cases khud load karega
    monitored_cases = get_all_monitored_cases()
    if not monitored_cases:
        print("ℹ️ No cases found in DB. Using fallback sample list...")
        monitored_cases = [
            "WPA/7974/2026", "WPA/14466/2026", "WPA/19235/2026",
            "WPA/16820/2026", "WPA/16201/2017", "WPA/6104/2024", "WPA/11035/2026"
        ]

    # 2. PDF load/fetch
    pdf_file = fetch_latest_cause_list("clause_list.pdf")
    if not pdf_file or not os.path.exists(pdf_file):
        print("❌ Pipeline stopped: PDF not available.")
        return

    # 3. Match
    matched = parse_cause_list(pdf_file, monitored_cases)
    
    # 4. Sync & Alert
    today_date = datetime.now().strftime("%Y-%m-%d")
    if matched:
        sync_to_supabase(matched)
        send_night_summary_telegram(matched, today_date)
        print("\n🎉 Night Pipeline Complete! DB synced and Telegram summary delivered.")
    else:
        print("\nℹ️ No target cases listed for hearing in this cause list.")


if __name__ == "__main__":
    run_night_pipeline()