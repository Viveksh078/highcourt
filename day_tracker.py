from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import threading
import time
from curl_cffi import requests
from supabase import Client, create_client

# --- Configurations ---
SUPABASE_URL = "https://ygboaajfqrryditrgzhu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlnYm9hYWpmcXJyeWRpdHJnemh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMDMxOTgsImV4cCI6MjEwNTY3OTE5OH0.prXkOtFTFgYnRhREh2wykEyCIgpo-nj55o8kzCekvWo"
TELEGRAM_BOT_TOKEN = "8892593538:AAEFB8hEyPI5612KC7iSVfrPKRp-IWmyhTs"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
LIVE_API_URL = "https://display.calcuttahighcourt.gov.in/display_api.json"


# --- Render Dummy Health Check Server ---
class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Munshi Day Tracker is Running 24x7!")


def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()


threading.Thread(target=run_dummy_server, daemon=True).start()


def send_telegram_alert(chat_id: str, message: str) -> bool:
    telegram_url = (
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        resp = requests.post(telegram_url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


def fetch_live_board():
    """High Court JSON API se live room numbers aur items fetch karta hai."""
    try:
        response = requests.get(
            LIVE_API_URL, impersonate="chrome120", timeout=15, verify=False
        )
        if response.status_code == 200:
            court_data = response.json()
            return {
                str(item.get("room_no")).strip(): item for item in court_data
            }
    except Exception as e:
        print(f"Notice: Court board offline or unreachable ({e})")
    return {}


def track_and_alert():
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔍 Checking active cases...")

    try:
        # Cases table se active cases aur advocate ka telegram chat id fetch karna
        res = (
            supabase.table("cases")
            .select("*, advocates(telegram_chat_id, full_name)")
            .execute()
        )
        all_cases = res.data or []
        active_cases = [
            c
            for c in all_cases
            if str(c.get("case_stage", "")).strip().lower() == "active"
        ]
    except Exception as err:
        print(f"Supabase read error: {err}")
        return

    print(
        f"Total cases: {len(all_cases)} | Active cases to track: {len(active_cases)}"
    )
    if not active_cases:
        return

    live_rooms = fetch_live_board()

    for item in active_cases:
        case_id = item.get("id")
        case_no = item.get("case_number", "Unknown")
        room_no = str(item.get("court_room", "")).strip()
        target_item = int(item.get("target_item", 0))

        # Advocate details
        adv_info = item.get("advocates") or {}
        chat_id = adv_info.get("telegram_chat_id") or item.get(
            "telegram_chat_id"
        )
        adv_name = adv_info.get("full_name", "Advocate")

        # Live Display Data match
        court_info = live_rooms.get(room_no)
        current_item = (
            court_info.get("cause_list_sr_no") if court_info else None
        )
        judge = (
            court_info.get("judge_names", "Hon'ble Bench")
            if court_info
            else "Hon'ble Bench"
        )

        # Fallback simulation if testing after court hours
        if current_item is None:
            print(
                f"Room {room_no}: Court offline, running simulation test (Target: {target_item})."
            )
            current_item = max(1, target_item - 2)

        diff = int(target_item) - int(current_item)
        print(
            f"--> Case: {case_no} | Room: {room_no} | Current: {current_item} | Target: {target_item} | Diff: {diff}"
        )

        # Alert Trigger: Jab 2 ya usse kam item bache hon
        if 0 <= diff <= 2:
            alert_msg = (
                f"🏛 *CALCUTTA HIGH COURT LIVE ALERT*\n\n"
                f"👨‍⚖️ *Advocate:* {adv_name}\n"
                f"📌 *Case:* `{case_no}`\n"
                f"📍 *Court Room:* `{room_no}`\n"
                f"⚖️ *Judge:* {judge}\n"
                f"⚡ *Current Running Item:* {current_item}\n"
                f"🎯 *Your Item:* {target_item}\n\n"
                f"🚨 *URGENT:* Aapka case aane mein sirf *{diff} items* bache hain! Court room ke bahar ready rahein."
            )
            if chat_id:
                print(f"Sending alert to Telegram ID: {chat_id}...")
                if send_telegram_alert(chat_id, alert_msg):
                    print(f"✅ Alert sent successfully!")
                    # Duplicate alerts rokne ke liye status update
                    supabase.table("cases").update(
                        {"case_stage": "Notified"}
                    ).eq("id", case_id).execute()
            else:
                print(f"⚠️ No telegram chat_id found for advocate.")


if __name__ == "__main__":
    print("🚀 MunshiAI Day Tracker Started...")
    print("Press Ctrl + C to stop.\n")
    while True:
        try:
            track_and_alert()
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n🛑 Tracker stopped.")
            break
        except Exception as e:
            print(f"Tracker Loop Error: {e}")
            time.sleep(10)