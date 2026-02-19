from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import time
import os

# ================= CONFIG =================
URL = "https://dookeela4.live/"
SAVE_DIR = "output"
OUTPUT_FILE = os.path.join(SAVE_DIR, "kl.txt")

REFERER = "https://dookeela4.live/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"
LOGO_IMAGE = "https://dookeela4.live/images/logo-bar.png"

# ตั้งค่าเวลาปัจจุบันแบบไทยสำหรับใช้ตั้งชื่อไฟล์หรือเช็คสถานะ Live
now_th = datetime.utcnow() + timedelta(hours=7)
today_short = now_th.strftime("%d/%m/%y")
today_full = now_th.strftime("%d/%m/%Y")

# ================= SELENIUM =================
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
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
finally:
    driver.quit()

# ================= PARSE MATCHES =================
matches = []
cards = soup.select("a[href^='/football/match/']")

for card in cards:
    try:
        match_url = "https://dookeela4.live" + card.get("href")
        
        league_name = "Unknown League"
        league_logo = LOGO_IMAGE
        league_block = card.select_one("div.mb-2")
        if league_block:
            img = league_block.find("img")
            if img:
                league_name = img.get("alt", "Unknown").strip()
                league_logo = img.get("src", LOGO_IMAGE)

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
                sort_time = now_th
                is_live = True
            else:
                parts = t.split()
                if len(parts) == 2:
                    # 1. ดึงวันที่และเวลาเดิมมา (ซึ่งเป็น UTC)
                    raw_date = parts[0]
                    raw_time = parts[1]
                    raw_dt = datetime.strptime(f"{raw_date} {raw_time}", "%d/%m/%y %H:%M")
                    
                    # 2. ✅ บวกเพิ่มไปเลย 7 ชั่วโมงให้เป็นเวลาไทย
                    th_dt = raw_dt + timedelta(hours=7)
                    
                    match_date = th_dt.strftime("%d/%m/%y")
                    match_time = th_dt.strftime("%H:%M")
                    sort_time = th_dt

        team_names = [span.text.strip() for span in card.select("div.flex.items-center.gap-2 span")]
        home = team_names[0] if len(team_names) > 0 else "-"
        away = team_names[1] if len(team_names) > 1 else "-"

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
    except:
        continue

# ================= GROUPING & SAVE =================
live_matches = []
date_groups = {}

for m in matches:
    if m["is_live"]:
        live_matches.append(m)
    else:
        date_groups.setdefault(m["date"], []).append(m)

groups = []
if live_matches:
    stations = []
    for m in live_matches:
        stations.append({
            "name": f"🔴 กำลังแข่ง {m['home']} vs {m['away']}",
            "info": m["league"],
            "image": m["league_logo"],
            "url": m["url"],
            "referer": REFERER,
            "userAgent": USER_AGENT
        })
    groups.append({"name": "🔴 Live Now", "image": LOGO_IMAGE, "stations": stations})

for date in sorted(date_groups.keys(), key=lambda x: datetime.strptime(x, "%d/%m/%y")):
    stations = []
    sorted_matches = sorted(date_groups[date], key=lambda x: x["sort_time"] if x["sort_time"] else datetime.max)
    for m in sorted_matches:
        stations.append({
            "name": f"{m['time']} {m['home']} vs {m['away']}",
            "info": m["league"],
            "image": m["league_logo"],
            "url": m["url"],
            "referer": REFERER,
            "userAgent": USER_AGENT
        })
    groups.append({"name": f"📅 วันที่ {date}", "image": LOGO_IMAGE, "stations": stations})

final_json = {
    "name": f"ดู dookeela4.live update @{today_full}",
    "groups": groups
}

os.makedirs(SAVE_DIR, exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_json, f, ensure_ascii=False, indent=2)

print(f"สร้างไฟล์เรียบร้อย (บวกเวลาไทยแล้ว) → {OUTPUT_FILE}")
