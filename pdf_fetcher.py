import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from curl_cffi import requests

NOTICES_URL = "https://www.calcuttahighcourt.gov.in/Notices"
BASE_DOMAIN = "https://www.calcuttahighcourt.gov.in"

def fetch_latest_cause_list(save_path="clause_list.pdf"):
    print("🔍 Fetching latest Appellate Side cause list from Calcutta High Court...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # Step 1: Portal ke notices page se latest cause list notice ID scan karein
        resp = requests.get(NOTICES_URL, impersonate="chrome120", headers=headers, timeout=25, verify=False)
        target_link = None
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                text = a_tag.get_text(strip=True).lower()
                if "Notice-Files/CL/" in href or ("cause" in text and "appellate" in text):
                    target_link = href if href.startswith("http") else f"{BASE_DOMAIN}/{href.lstrip('/')}"
                    print(f"🎯 Found live link: {a_tag.get_text(strip=True)} -> {target_link}")
                    break

        # Fallback: Agar landing link direct na mile toh existing working PDF use karo
        if not target_link:
            print("ℹ️ Using local verified cause list file...")
            if os.path.exists("clause_list.pdf"):
                return "clause_list.pdf"
            return None

        # Step 2: Download the PDF
        print(f"⬇️ Downloading: {target_link}")
        pdf_resp = requests.get(target_link, impersonate="chrome120", headers=headers, timeout=120, verify=False)
        
        if pdf_resp.status_code == 200 and pdf_resp.content.startswith(b"%PDF"):
            with open(save_path, "wb") as f:
                f.write(pdf_resp.content)
            size_mb = round(len(pdf_resp.content) / (1024 * 1024), 2)
            print(f"✅ Download complete: {save_path} ({size_mb} MB)")
            return save_path
        else:
            print("⚠️ Live download returned non-PDF, falling back to local file.")
            return "clause_list.pdf" if os.path.exists("clause_list.pdf") else None

    except Exception as e:
        print(f"⚠️ Fetching note: {e}, falling back to local clause_list.pdf")
        return "clause_list.pdf" if os.path.exists("clause_list.pdf") else None

if __name__ == "__main__":
    fetch_latest_cause_list()