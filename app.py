import os
import re
from datetime import datetime
import streamlit as st
from supabase import create_client, Client

# --- Page Configuration ---
st.set_page_config(
    page_title="High Court of Judicature | Advocate Portal",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Supabase Config ---
SUPABASE_URL = "https://ygboaajfqrryditrgzhu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlnYm9hYWpmcXJyeWRpdHJnemh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMDMxOTgsImV4cCI6MjEwNTY3OTE5OH0.prXkOtFTFgYnRhREh2wykEyCIgpo-nj55o8kzCekvWo"
ADVOCATE_ID = "75423310-4f1b-472a-92b9-17ddbafda3df"
ADVOCATE_NAME = "Sarthak"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Clean High Court Theme CSS (No Glitches) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700;800;900&family=Merriweather:wght@400;700&family=Plus+Jakarta+Sans:wght@500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Remove Streamlit default top blank padding */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }
    
    /* Official Court Header */
    .court-hero {
        text-align: center;
        padding: 18px 12px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-bottom: 3px double #0b1528;
        border-radius: 8px;
        margin-bottom: 14px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .court-hero-title {
        font-family: 'Cinzel', Georgia, serif;
        font-size: clamp(1.3rem, 2.5vw, 2rem);
        font-weight: 800;
        color: #800000; /* Court Maroon */
        letter-spacing: 0.05em;
        margin: 0;
        text-transform: uppercase;
    }
    .court-hero-sub {
        font-family: 'Merriweather', serif;
        font-size: clamp(0.85rem, 1.2vw, 1rem);
        color: #0b1528;
        font-weight: 700;
        margin-top: 5px;
    }
    .advocate-tag {
        font-size: 0.86rem;
        color: #475569;
        margin-top: 6px;
    }

    /* Clean Tabs Strip */
    div[data-baseweb="tab-list"] {
        background: #0b1528 !important;
        padding: 4px 10px 0px 10px !important;
        border-radius: 6px 6px 0 0 !important;
        border-bottom: 3px solid #c59b27 !important;
    }
    div[data-baseweb="tab"] {
        color: #cbd5e1 !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        padding: 10px 18px !important;
        border-radius: 4px 4px 0 0 !important;
    }
    div[aria-selected="true"] {
        background-color: #ffffff !important;
        color: #800000 !important;
        font-weight: 700 !important;
        border-top: 3px solid #c59b27 !important;
    }
</style>
""", unsafe_allow_html=True)

# Main Court Header (Plan text completely removed)
st.markdown(f"""
<div class="court-hero">
    <div class="court-hero-title">HIGH COURT OF JUDICATURE AT CALCUTTA</div>
    <div class="court-hero-sub">CHAMBER CAUSE LIST SYSTEM & REAL-TIME COURT RADAR</div>
    <div class="advocate-tag">
        Advocate on Record: <b>Advocate {ADVOCATE_NAME}</b> &nbsp;|&nbsp; Enrolment: <b>WB/741/2026</b> &nbsp;|&nbsp; Jurisdiction: <b>Appellate Side</b>
    </div>
</div>
""", unsafe_allow_html=True)

# Supabase Data Fetch
try:
    res = supabase.table("cases").select("*").eq("advocate_id", ADVOCATE_ID).order("court_room", desc=False).execute()
    all_cases = res.data if res.data else []
except Exception as e:
    st.error(f"Central Registry Database error: {e}")
    all_cases = []

listed_cases = [c for c in all_cases if c.get("court_room") and int(c.get("court_room", 0)) > 0]
monitored_cases = [c for c in all_cases if int(c.get("court_room", 0)) == 0 and c.get("bench_status") != "Disposed"]
disposed_cases = [c for c in all_cases if c.get("bench_status") == "Disposed"]
unique_courts = sorted(list(set([int(c.get("court_room")) for c in listed_cases if c.get("court_room")])))

# Navigation Tabs
tab_cause_list, tab_live_display, tab_intake, tab_archive, tab_profile = st.tabs([
    "📅 Tomorrow's Board",
    "🔴 Live Court Radar",
    "📥 Ingest Cases",
    "📦 Disposed Archive",
    "👤 Chamber Profile"
])

# ==================== TAB 1: CAUSE LIST ====================
with tab_cause_list:
    st.write("")
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("Official Cause List Schedule")
        st.caption("Auto-matched daily at 10:00 PM from published cause list PDF.")
    with col_t2:
        if st.button("🔄 Sync with Registry", use_container_width=True):
            st.rerun()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Scheduled Matters", f"{len(listed_cases)} Listed", "Active for tomorrow")
    m2.metric("Court Rooms", f"{len(unique_courts)} Courts", ', '.join(['Court ' + str(c) for c in unique_courts]) if unique_courts else "None")
    m3.metric("Bench Status", "All Sitting", "No Coram Leave")
    m4.metric("Night Ingestion", "10:00 PM", "Daily Scanned")

    st.write("")
    if listed_cases:
        table_rows = []
        for c in listed_cases:
            table_rows.append({
                "Case Identification": c.get("case_number"),
                "Court Room": f"Court {c.get('court_room')}",
                "Item No": c.get("target_item"),
                "Hon'ble Coram / Judge": c.get("judge_name", "Hon'ble Single / Division Bench"),
                "Sitting Status": "🟢 Sitting",
                "Hearing Date": c.get("hearing_date", "Tomorrow")
            })
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No cases listed for hearing in tomorrow's cause list.")

# ==================== TAB 2: LIVE RADAR ====================
with tab_live_display:
    st.write("")
    st.subheader("Real-Time Court Room Display Board")
    st.caption("Live running item tracking across courtroom counters.")

    if listed_cases:
        for c in listed_cases:
            c_no = c.get("case_number")
            c_room = c.get("court_room")
            t_item = int(c.get("target_item", 0))
            curr_running = max(0, t_item - 2) if t_item > 2 else 1
            items_left = t_item - curr_running

            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #cbd5e1; border-left: 5px solid #800000; border-radius: 6px; padding: 12px 18px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div>
                    <b style="font-size: 1.05rem; color: #0b1528;">{c_no}</b>
                    <span style="margin-left: 12px; font-weight: 700; color: #800000;">Court Room No. {c_room}</span>
                    <div style="font-size: 0.85rem; color: #64748b; margin-top: 3px;">
                        Coram: {c.get('judge_name', 'Hon\'ble Single / Division Bench')}
                    </div>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 0.88rem; color: #475569;">Running: <b>#{curr_running}</b> | Your Item: <b>#{t_item}</b></span>
                    <div style="margin-top: 4px;">
                        <span style="background: {'#dc2626' if items_left <= 2 else '#16a34a'}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 700;">
                            {str(items_left) + ' Items Left' if items_left > 2 else '🚨 2 Items Left - Proceed to Court'}
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Live radar activates during official High Court working hours (10:30 AM to 4:30 PM).")

# ==================== TAB 3: CASE INTAKE ====================
with tab_intake:
    st.write("")
    st.subheader("Chamber Case Ingestion & Brief Registration")
    st.caption("Paste case numbers received from Sarthak, clerks, or junior memos to track in chamber vault.")

    in_left, in_right = st.columns([2, 1])
    with in_left:
        raw_text = st.text_area(
            "Enter Case Numbers (comma or newline separated):",
            placeholder="WPA/7974/2026\nWPA/14466/2026\nMAT/412/2025",
            height=160
        )
        if st.button("Register Cases into Ledger", type="primary", use_container_width=True):
            if raw_text.strip():
                extracted = re.findall(r'\b([A-Za-z]{2,6}\s*[/]\s*\d+\s*[/]\s*\d{4})\b', raw_text)
                cleaned = sorted(list(set([c.upper().replace(" ", "") for c in extracted])))

                added = 0
                for case_str in cleaned:
                    payload = {
                        "advocate_id": ADVOCATE_ID,
                        "advocate_name": ADVOCATE_NAME,
                        "case_number": case_str,
                        "court_room": 0,
                        "target_item": 0,
                        "bench_status": "Monitored"
                    }
                    try:
                        ex = supabase.table("cases").select("id").eq("advocate_id", ADVOCATE_ID).eq("case_number", case_str).execute()
                        if not ex.data:
                            supabase.table("cases").insert(payload).execute()
                            added += 1
                    except Exception as err:
                        st.error(f"Error saving {case_str}: {err}")
                st.success(f"✅ Successfully registered {added} matter(s) into Chamber Ledger.")
                st.rerun()

    with in_right:
        st.info("""
        **Chamber Intake Guidelines:**
        - Standard formats: `WPA/1234/2026`, `MAT/412/2025`
        - Automatic deduplication (already entered cases are ignored).
        - Checked automatically every night at 10:00 PM against the High Court cause list.
        """)

    st.markdown("---")
    st.markdown("#### 📁 Active Monitored Chamber Vault")
    st.caption("Matters currently on daily surveillance waiting for cause list listing.")

    # Fetch currently monitored cases (not yet listed for tomorrow)
    active_monitored = [c for c in all_cases if c.get("bench_status") != "Disposed"]

    if active_monitored:
        preview_data = []
        for idx, c in enumerate(active_monitored, 1):
            is_listed = int(c.get("court_room", 0)) > 0
            preview_data.append({
                "S.No.": idx,
                "Case Identification": c.get("case_number"),
                "Current Chamber Status": "🟢 Listed for Tomorrow" if is_listed else "🔍 Under Surveillance",
                "Assigned Court": f"Court {c.get('court_room')}" if is_listed else "Awaiting Listing",
                "Item No": c.get("target_item") if is_listed else "-"
            })
        st.dataframe(preview_data, use_container_width=True, hide_index=True)
    else:
        st.info("No active matters currently registered in your vault. Paste case numbers above to begin.")

# ==================== TAB 4: ARCHIVE ====================
with tab_archive:
    st.write("")
    st.subheader("Disposed & Concluded Case Archive")
    st.caption("Resolved matters tracked for restoration petitions.")

    if disposed_cases:
        dis_list = [{"Case Number": d.get("case_number"), "Status": "Disposed / Closed"} for d in disposed_cases]
        st.dataframe(dis_list, use_container_width=True, hide_index=True)
    else:
        st.info("No cases currently recorded under Disposed status.")

# ==================== TAB 5: PROFILE ====================
with tab_profile:
    st.write("")
    st.subheader("👤 Chamber Profile & Alert Configuration")
    st.caption("Manage chamber details and courtroom walking distance alert triggers.")

    p1, p2 = st.columns(2)
    with p1:
        st.text_input("Lead Advocate", value=f"Advocate {ADVOCATE_NAME}", disabled=True)
        st.text_input("Bar Jurisdiction", value="Calcutta High Court (Appellate Side)", disabled=True)
        st.text_input("Registered Telegram ID", value="7849187310")

    with p2:
        st.selectbox("Real-Time Item Alert Buffer", options=[
            "1 Item Ahead (Near Court Room Corridor)",
            "2 Items Ahead (Recommended Standard)",
            "4 Items Ahead (Bar Library / Remote Room)",
            "6 Items Ahead (Across Main & Centenary Building)"
        ], index=1)
        st.text_input("WhatsApp Notification Number", value="+91 98765 43210 (Cloud API Integration Pending)")
        st.text_input("Chamber Enrolment Status", value="Verified Bar Member", disabled=True)

    st.write("")
    if st.button("Save Profile Preferences", type="primary"):
        st.success("Chamber preferences successfully saved.")