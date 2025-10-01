#!/usr/bin/env python3
"""Fetch a small curated set of team logos (public Wikimedia assets) for teams present in the Singapore prediction CSV.
This is a one-off helper that uses safe headers and writes to assets/logos/.
"""
from pathlib import Path
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'
logo_dir = ROOT / 'assets' / 'logos'
logo_dir.mkdir(parents=True, exist_ok=True)

csvp = ART / 'prediction_singapore_full.csv'
if not csvp.exists():
    raise SystemExit('prediction_singapore_full.csv not found in artifacts/')

df = pd.read_csv(csvp)
teams = sorted(df['TeamName'].dropna().unique().tolist())
print('Teams in predictions:', teams)

# curated mapping (team string -> PNG URL)
mapping = {
    'Red Bull Racing': 'https://upload.wikimedia.org/wikipedia/en/5/51/Red_Bull_Racing_Logo.svg',
    'McLaren': 'https://upload.wikimedia.org/wikipedia/commons/6/62/McLaren_Racing_logo.svg',
    'Mercedes': 'https://upload.wikimedia.org/wikipedia/commons/9/90/Mercedes-Benz_logo_2010.svg',
    'Ferrari': 'https://upload.wikimedia.org/wikipedia/en/d/d9/Scuderia_Ferrari_Logo.svg',
    'Aston Martin': 'https://upload.wikimedia.org/wikipedia/en/8/8f/Aston_Martin_F1_Logo.svg',
    'Kick Sauber': 'https://upload.wikimedia.org/wikipedia/en/5/59/Sauber_Formula_1_Logo.png',
    'Williams': 'https://upload.wikimedia.org/wikipedia/en/8/80/Williams_Racing_logo.svg',
    'Alpine': 'https://upload.wikimedia.org/wikipedia/commons/2/28/Alpine_F1_Team_logo.svg',
    'Haas F1 Team': 'https://upload.wikimedia.org/wikipedia/en/7/7f/Haas_F1_Team_logo.svg',
    'AlphaTauri': 'https://upload.wikimedia.org/wikipedia/commons/7/72/Scuderia_AlphaTauri_logo.svg',
    'RB': 'https://upload.wikimedia.org/wikipedia/en/5/51/Red_Bull_Racing_Logo.svg',
    'Racing Bulls': 'https://upload.wikimedia.org/wikipedia/en/5/51/Red_Bull_Racing_Logo.svg'
}

headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.google.com/'}

def sanitize(name: str) -> str:
    return ''.join([ch for ch in str(name) if ch.isalnum() or ch in (' ','-')]).replace(' ','_')

for t in teams:
    url = mapping.get(t)
    if not url:
        print('No mapping for', t)
        continue
    # try to fetch the SVG or PNG and save as PNG when possible
    dest = logo_dir / (sanitize(t) + '.png')
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        content = r.content
        # if SVG, try to save raw svg as png extension (browsers will still render if inlined as SVG data-url)
        dest.write_bytes(content)
        print('Wrote', dest)
    except Exception as e:
        print('Failed to download', t, url, 'err:', e)

print('Done')
