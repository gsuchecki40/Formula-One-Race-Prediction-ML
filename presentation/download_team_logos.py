#!/usr/bin/env python3
"""Download team logos into assets/logos/ from a CSV mapping.

CSV format (header): TeamName,URL
Example:
"Red Bull Racing",https://example.com/logos/red_bull_racing.png

The script will sanitize team names to match the existing `generate_singapore_report.py` convention
and save files as `assets/logos/{sanitized}.png`.

Usage:
  python3 presentation/download_team_logos.py --input presentation/logo_urls.csv
  python3 presentation/download_team_logos.py --input presentation/logo_urls.csv --dry-run
"""
from pathlib import Path
import csv
import argparse
import requests
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
logo_dir = ROOT / 'assets' / 'logos'
logo_dir.mkdir(parents=True, exist_ok=True)

def sanitize(name: str) -> str:
    return ''.join([ch for ch in str(name) if ch.isalnum() or ch in (' ','-')]).replace(' ','_')

def download(url: str, dest: Path, timeout=20):
    # use common browser user-agent and referer to avoid simple 403 blocks
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15',
        'Referer': 'https://www.google.com/'
    }
    with requests.get(url, timeout=timeout, headers=headers, stream=True) as resp:
        resp.raise_for_status()
        # write in chunks
        with dest.open('wb') as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', '-i', required=True, help='CSV file with TeamName,URL')
    p.add_argument('--dry-run', action='store_true', help='Do not download; just show mapping')
    p.add_argument('--wait', type=float, default=0.5, help='Seconds to wait between downloads')
    args = p.parse_args()

    csvp = Path(args.input)
    if not csvp.exists():
        print('Input CSV not found:', csvp)
        sys.exit(1)

    rows = []
    with csvp.open() as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            if 'TeamName' in r and 'URL' in r:
                rows.append((r['TeamName'].strip(), r['URL'].strip()))
            else:
                print('CSV must contain TeamName and URL columns; found:', reader.fieldnames)
                sys.exit(1)

    print('Found', len(rows), 'rows to process')
    for team, url in rows:
        safe = sanitize(team)
        dest = logo_dir / (safe + '.png')
        print(team, '->', dest.name)
        if args.dry_run:
            continue
        try:
            print('Downloading', url)
            download(url, dest)
            time.sleep(args.wait)
        except Exception as e:
            print('Failed to download', url, 'error:', e)

    print('Done. Logos saved to', logo_dir)

if __name__ == '__main__':
    main()
