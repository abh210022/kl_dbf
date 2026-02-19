from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta # เพิ่ม timedelta เพื่อใช้บวกเวลา
import json
import time
import os

# ================= CONFIG (ปรับปรุงสำหรับ GitHub) =================
URL = "https://dookeela4.live/"
SAVE_DIR = "output"
OUTPUT_FILE = os.path.join(SAVE_DIR, "kl.txt")

REFERER = "https://dookeela4.live/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"
LOGO_IMAGE = "https://dookeela4.live/images/logo-bar.png"

# ✅ ปรับเวลา 'ตอนนี้' ให้เป็นเวลาไทย เพื่อใช้เช็คคู่ที่กำลังแข่ง
now = datetime.utcnow() + timedelta(hours=7)
today_short = now.strftime("%d/%m/%y")
today_full = now.strftime("%d/%m/%Y")

# ================= SELENIUM (ปรับปรุงสำหรับ Linux/GitHub) =================
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument(f"user-agent={USER_AGENT}")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

driver.get(URL)

try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
finally:
    driver.quit()

# ================= PARSE MATCHES (คงกระบวนการเดิม แก้เฉพาะเวลา) =================
matches = []
cards = soup.select("a[href^='/football/match/']")

for card in cards:
    try:
        match_url = "https://dookeela4.live" + card.get("href")

        # ----- League -----
        league_name = "Unknown League"
        league_logo = LOGO_IMAGE
        league_block = card.select_one("div.mb-2")
        if league_block:
            img = league_block.find("img")
            if img:
                if img.get("alt"):
                    league_name = img.get("alt").strip()
                if img.get("src"):
                    league_logo = img.get("src")

        # ----- Date / Time -----
        match_date = None
        match_time = None
        sort_time = None
        is_live = False
        time_span = card.select_one("div.mb-2 span.text-sub")
        
        if time_span:
            t = time_span.text.strip()
            if "กำลังดู" in t:
                match_date = today_short
                match_time = "กำลังแข่ง"
                sort_time = now
                is_live = True
            else:
                parts = t.split()
                if len(parts) == 2:
                    # ดึงวันที่/เวลาเดิม (UTC)
                    raw_date = parts[0]
                    raw_time = parts[1]
                    raw_dt = datetime.strptime(f"{raw_date} {raw_time}", "%d/%m/%y %H:%M")
                    
                    # ✅ บวกเพิ่ม 7 ชั่วโมงให้เป็นเวลาไทย
                    th_dt = raw_dt + timedelta(hours=7)
                    
                    match_date = th_dt.strftime("%d/%m/%y")
                    match_time = th_dt.strftime("%H:%M")
                    sort_time = th_dt

        # ----- Teams -----
        team_row = None
        for r in card.select("div.flex.items-center.justify-between"):
            if "mb-2" not in r.get("class", []):
                team_row = r
                break

        home = away = "-"
        if team_row:
            teams = team_row.select("div.flex.items-center.gap-2")
            if len(teams) >= 2:
                home = teams[0].find("span").text.strip()
                away = teams[1].find("span").text.strip()

        if match_date:
            matches.append({
                "date": match_date,
                "time": match_time,
                "sort_time": sort_time,
                "home": home,
                "away": away,
                "league": league_name,
                "league_logo": league_logo,
                "url": match_url,
                "is_live": is_live
            })
    except Exception:
        continue

# ================= GROUPING & FINAL JSON (เหมือนเดิม) =================
live_matches = []
date_groups = {}

for m in matches:
    if m["is_live"]:
        live_matches.append(m)
    else:
        date_groups.setdefault(m["date"], []).append(m)

def time_sort_key(m):
    return m["sort_time"] if m["sort_time"] else datetime.max

def parse_date_key(date_str):
    return datetime.strptime(date_str, "%d/%m/%y")

groups = []

if live_matches:
    live_stations = []
    for m in live_matches:
        live_stations.append({
            "name": f"กำลังแข่ง {m['home']} vs {m['away']}",
            "info": m["league"],
            "image": m["league_logo"],
            "url": m["url"],
            "referer": REFERER,
            "userAgent": USER_AGENT
        })
    groups.append({"name": "🔴Live", "image": LOGO_IMAGE, "stations": live_stations})

for date in sorted(date_groups.keys(), key=parse_date_key):
    stations = []
    for m in sorted(date_groups[date], key=time_sort_key):
        stations.append({
            "name": f"{m['time']} {m['home']} vs {m['away']}",
            "info": m["league"],
            "image": m["league_logo"],
            "url": m["url"],
            "referer": REFERER,
            "userAgent": USER_AGENT
        })
    groups.append({"name": f"วันที่ {date}", "image": LOGO_IMAGE, "stations": stations})

final_json = {
    "name": f"ดู dookeela4.live update @{today_full}",
    "author": f"Update@{today_full}",
    "info": f"dookeela4.live Update@{today_full}",
    "image": LOGO_IMAGE,
    "groups": groups
}

# ================= SAVE =================
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_json, f, ensure_ascii=False, indent=2)

print(f"สร้างไฟล์เรียบร้อย → {OUTPUT_FILE}")
