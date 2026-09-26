import re
from curl_cffi import requests
from supabase import create_client, Client

# --- Configurations ---
SUPABASE_URL = "https://ygboaajfqrryditrgzhu.supabase.co"
# Apni working Supabase Key yahan paste karein (day_tracker.py wali)
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlnYm9hYWpmcXJyeWRpdHJnemh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMDMxOTgsImV4cCI6MjEwNTY3OTE5OH0.prXkOtFTFgYnRhREh2wykEyCIgpo-nj55o8kzCekvWo"
ADVOCATE_ID = "75423310-4f1b-472a-92b9-17ddbafda3df"
ADVOCATE_NAME = "Sarthak"

# Telegram Bot Config (day_tracker.py wala)
TELEGRAM_BOT_TOKEN = "8892593538:AAEFB8hEyPI5612KC7iSVfrPKRp-IWmyhTs"
TELEGRAM_CHAT_ID = "5834882829"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Regex pattern jo multiple High Court case formats capture karta hai:
# Examples: WPA/123/2026, MAT/45/2025, CRR/89/2024, FMA/12/2026, etc.
CASE_REGEX = re.compile(r'\b([A-Za-z]{2,6}\s*[/]\s*\d+\s*[/]\s*\d{4})\b')

def notify_telegram_new_cases(cases_added, sender_email):
    """Telegram par alert bhejta hai jab naye cases add hote hain."""
    if not TELEGRAM_BOT_TOKEN or "PASTE" in TELEGRAM_BOT_TOKEN:
        print("⚠️ Telegram token not configured, skipping alert.")
        return
        
    lines = [
        "📥 <b>New Cases Ingested via Email</b>\n",
        f"From: <code>{sender_email}</code>",
        f"Advocate Vault: <b>{ADVOCATE_NAME}</b>",
        f"Cases Added: <b>{len(cases_added)}</b>\n",
        "────────────────────────"
    ]
    for c in cases_added:
        lines.append(f"⚖️ <code>{c}</code>")
        
    lines.append("────────────────────────")
    lines.append("✅ <i>Added to Monitored Cases list. Night worker will scan these tonight.</i>")
    
    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
        if r.status_code == 200:
            print("📲 Telegram notification delivered successfully!")
        else:
            print(f"⚠️ Telegram error: {r.text}")
    except Exception as e:
        print(f"⚠️ Telegram network error: {e}")

def simulate_email_receipt():
    # Yeh ek realistic email body hai jo junior/clerk bhejte hain
    mock_email_sender = "sarthak.chamber@gmail.com"
    mock_email_body = """
    Respected Sir,
    
    Please find below the list of new matters assigned to our chamber this week:
    
    1. WPA/8821/2026 - State of West Bengal vs Ghosh
    2. MAT/412/2025 - Municipal Corp matter
    3. FMA/1502/2024 - Appeal case
    4. CRR/993/2026 - Criminal revision petition
    
    Also kindly keep track of pending case WPA / 5512 / 2026.
    
    Regards,
    Sarthak (Chamber Junior)
    """

    print("📬 [Simulating] Incoming email received...")
    print(f"   From: {mock_email_sender}")
    print("   Scanning email content for High Court case numbers...")

    # Regex extraction
    raw_matches = CASE_REGEX.findall(mock_email_body)
    # Formatting clean: Spaces hatana aur uppercase banana
    clean_cases = [c.upper().replace(" ", "") for c in raw_matches]
    clean_cases = sorted(list(set(clean_cases)))

    print(f"\n🎯 Discovered {len(clean_cases)} valid case(s) in email:")
    for c in clean_cases:
        print(f"   👉 {c}")

    # Database sync (Master Vault mein add/check karna)
    print("\n💾 Ingesting into Supabase Vault...")
    saved_cases = []
    for c in clean_cases:
      payload = {
          "advocate_id": ADVOCATE_ID,
          "advocate_name": ADVOCATE_NAME,
          "case_number": c,
          "court_room": 0,
          "target_item": 0,  # <-- Added default 0
          "bench_status": "Monitored",
      }
      try:
        # Check existing
        existing = (
            supabase.table("cases")
            .select("id")
            .eq("advocate_id", ADVOCATE_ID)
            .eq("case_number", c)
            .execute()
        )
        if existing.data:
          supabase.table("cases").update(payload).eq(
              "id", existing.data[0]["id"]
          ).execute()
          print(f"   🔄 Updated existing case: {c}")
        else:
          supabase.table("cases").insert(payload).execute()
          print(f"   ✅ Inserted new case: {c}")
        saved_cases.append(c)
      except Exception as e:
        print(f"   ❌ Error saving {c}: {e}")

    # Telegram notification
    if saved_cases:
        print("\n📲 Dispatching Telegram alert to advocate...")
        notify_telegram_new_cases(saved_cases, mock_email_sender)

    print("\n🎉 Test Complete! Cases successfully ingested from email simulation.")

if __name__ == "__main__":
    simulate_email_receipt()