#!/usr/bin/env python3
"""
fetch-commercial-harvest.py
Fetches ADF&G commercial salmon harvest summaries by management area.
Generates live-commercial.json for the alaskafishdata app.
Sources: ADF&G weekly in-season reports, CFEC daily fish ticket estimates.
"""
import json
import re
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

ADFG_BASE = "https://www.adfg.alaska.gov"

# ADF&G in-season harvest report pages by area
AREA_PAGES = {
    "bristol-bay": {
        "name": "Bristol Bay Management Area",
        "region": "Bristol Bay",
        "url": f"{ADFG_BASE}/index.cfm?adfg=commercialbyarea.bristolbay",
        "primary_species": ["Sockeye"],
        "2024_baseline_harvest": 41600000,
        "2024_baseline_exvessel": 128500000,
        "permits": 1840,
    },
    "southeast-alaska": {
        "name": "Southeast Alaska (Panhandle)",
        "region": "Southeast",
        "url": f"{ADFG_BASE}/index.cfm?adfg=commercialbyarea.se",
        "primary_species": ["Pink", "Chum", "Coho", "Chinook"],
        "2024_baseline_harvest": 38200000,
        "2024_baseline_exvessel": 64100000,
        "permits": 1150,
    },
    "prince-william-sound": {
        "name": "Prince William Sound & Copper River",
        "region": "Prince William Sound",
        "url": f"{ADFG_BASE}/index.cfm?adfg=commercialbyarea.pwscopper",
        "primary_species": ["Sockeye", "Pink", "Chinook"],
        "2024_baseline_harvest": 28400000,
        "2024_baseline_exvessel": 48200000,
        "permits": 720,
    },
    "kodiak": {
        "name": "Kodiak Management Area",
        "region": "Kodiak",
        "url": f"{ADFG_BASE}/index.cfm?adfg=commercialbyarea.kodiak",
        "primary_species": ["Pink", "Sockeye"],
        "2024_baseline_harvest": 22800000,
        "2024_baseline_exvessel": 32400000,
        "permits": 480,
    },
    "area-m": {
        "name": "Alaska Peninsula & Aleutians (Area M)",
        "region": "Westward",
        "url": f"{ADFG_BASE}/index.cfm?adfg=commercialbyarea.areaMpennAleut",
        "primary_species": ["Sockeye", "Pink"],
        "2024_baseline_harvest": 19400000,
        "2024_baseline_exvessel": 26800000,
        "permits": 390,
    },
    "cook-inlet": {
        "name": "Cook Inlet (Upper & Lower)",
        "region": "Southcentral",
        "url": f"{ADFG_BASE}/index.cfm?adfg=commercialbyarea.upperCookInlet",
        "primary_species": ["Sockeye", "Pink"],
        "2024_baseline_harvest": 8500000,
        "2024_baseline_exvessel": 14200000,
        "permits": 510,
    },
    "chignik": {
        "name": "Chignik Management Area",
        "region": "Westward",
        "url": f"{ADFG_BASE}/index.cfm?adfg=commercialbyarea.chignik",
        "primary_species": ["Sockeye"],
        "2024_baseline_harvest": 6100000,
        "2024_baseline_exvessel": 9800000,
        "permits": 85,
    },
    "norton-sound-kotzebue": {
        "name": "Norton Sound & Kotzebue",
        "region": "Arctic-Yukon-Kuskokwim",
        "url": f"{ADFG_BASE}/index.cfm?adfg=commercialbyarea.nortonSound",
        "primary_species": ["Chum"],
        "2024_baseline_harvest": 2100000,
        "2024_baseline_exvessel": 2400000,
        "permits": 120,
    },
}


def try_scrape_live(area_info: dict) -> dict | None:
    """Attempt to scrape live harvest data from ADF&G page."""
    try:
        resp = requests.get(area_info["url"], timeout=15, headers={
            "User-Agent": "AlaskaFishData/1.0 (+https://alaskafishdata.com)"
        })
        if not resp.ok:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ", strip=True)

        # Try to find harvest numbers in page text
        # ADF&G often shows "X million fish" or "X,XXX,XXX" patterns
        numbers = re.findall(r'[\d,]+(?:\.\d+)?(?:\s*million)?', text)
        harvest_candidate = None
        for n in numbers:
            clean = n.replace(",", "").replace(" million", "000000").strip()
            try:
                val = float(clean)
                if 100000 < val < 200000000:  # Plausible range
                    harvest_candidate = int(val)
                    break
            except:
                pass

        return harvest_candidate

    except Exception:
        return None


def main():
    now = datetime.now(timezone.utc)
    season = now.year
    is_in_season = 5 <= now.month <= 10  # May-October

    print(f"Fetching commercial harvest data (season {season}, in_season={is_in_season})...")

    areas = []
    for area_id, info in AREA_PAGES.items():
        print(f"  Processing {info['name']}...")

        # Try live scrape first; fall back to stored baseline
        live_harvest = None
        if is_in_season:
            live_harvest = try_scrape_live(info)

        harvest = live_harvest if live_harvest else info["2024_baseline_harvest"]
        status = "Live" if live_harvest else "2024 Baseline"

        areas.append({
            "id": area_id,
            "name": info["name"],
            "region": info["region"],
            "harvest": harvest,
            "exVessel": info["2024_baseline_exvessel"],
            "permits": info["permits"],
            "status": status,
            "primarySpecies": info["primary_species"],
            "season": str(season),
            "source_url": info["url"],
            "fetched_at": now.isoformat(),
        })

    # Sort by harvest descending
    areas.sort(key=lambda a: a["harvest"], reverse=True)

    with open("data/live-commercial.json", "w") as f:
        json.dump(areas, f, indent=2)

    total = sum(a["harvest"] for a in areas)
    print(f"\n  ok data/live-commercial.json: {len(areas)} areas, {total:,} total fish")


if __name__ == "__main__":
    main()
