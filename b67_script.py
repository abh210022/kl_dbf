from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
import time
import os
import json
from collections import defaultdict
from datetime import datetime

# ---------------- CONFIG (Updated for GitHub) ----------------
URL = "https://ball67.com/"
SAVE_DIR = "output"
OUTPUT_FILE = os.path.join(SAVE_DIR, "b67m.txt")

SITE_LOGO = "https://img2.pic.in.th/sitelogo.md.png"
REFERER = "https://ball67.com/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"

# ---------------- Selenium (Updated for GitHub) ----------------
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument(f"user-agent={UA}")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    driver.get(URL)
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "livefixtures-wrapper"))
    )
    time.sleep(3)
    html = driver.page_source
finally:
    driver.quit()

# ---------------- Parse (คงเดิม) ----------------
soup = BeautifulSoup(html, "html.parser")
groups_by_date = defaultdict(list)
match_count = 0

leagues = soup.select("#livefixtures-wrapper > div > div.rounded-xl")

for league in leagues:
    league_header = league.select_one("div.bg-gradient-to-r")
    if not league_header: continue

    league_name_raw = league_header.select_one("h2").get_text(" ", strip=True)
    league_name = " ".join(league_name_raw.split())
    matches = league.select("a[href^='/live/']")

    for match in matches:
        status_raw = match.select_one(".match-status").get_text("\n", strip=True)
        parts = [p.strip() for p in status_raw.split("\n") if p.strip()]

        if len(parts) != 2: continue

        time_text, date_text = parts
        link = "https://ball67.com" + match["href"]
        teams = match.select(".space-y-3 > div")
        if len(teams) < 2: continue

        home_img = teams[0].select_one("img")["src"]
        home_name = teams[0].select_one("div.flex-1").get_text(strip=True)
        away_name = teams[1].select_one("div.flex-1").get_text(strip=True)

        station = {
            "name": f"{time_text} {home_name} vs {away_name}",
            "info": league_name,
            "image": home_img,
            "url": link,
            "referer": REFERER,
            "userAgent": UA
        }
        groups_by_date[date_text].append(station)
        match_count += 1

# ---------------- Sort & Build JSON ----------------
def parse_date(d): return datetime.strptime(d, "%d/%m/%y")
def parse_time(station_name):
    t = station_name.split(" ")[0]
    try: return datetime.strptime(t, "%H:%M")
    except: return datetime.strptime("23:59", "%H:%M")

sorted_dates = sorted(groups_by_date.keys(), key=parse_date)
today_str = datetime.now().strftime("%d/%m/%Y")

groups = []
for date_text in sorted_dates:
    stations_sorted = sorted(groups_by_date[date_text], key=lambda s: parse_time(s["name"]))
    groups.append({"name": f"วันที่ {date_text}", "image": SITE_LOGO, "stations": stations_sorted})

data = {
    "name": f"ball67 update @{today_str}",
    "author": f"Update@{today_str}",
    "info": f"ball67 Update@{today_str}",
    "image": SITE_LOGO,
    "groups": groups
}

# ---------------- Save File ----------------
os.makedirs(SAVE_DIR, exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"บันทึกไฟล์เรียบร้อย: {OUTPUT_FILE}")
print(f"จำนวนคู่ที่ดึงได้: {match_count} คู่")