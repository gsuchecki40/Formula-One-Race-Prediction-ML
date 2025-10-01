#!/usr/bin/env python3
"""Generate a small HTML report for the Singapore prediction artifacts.

Reads artifacts/prediction_singapore_full.csv and related files, computes gap-from-winner,
and writes presentation/prediction_singapore_report.html embedding images and a tidy table.
"""
from pathlib import Path
import pandas as pd
import html
import base64

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'
OUT = ROOT / 'presentation'
OUT.mkdir(exist_ok=True)

# files we expect
pred_full = ART / 'prediction_singapore_full.csv'
tyre_counts = ART / 'prediction_singapore_tyre_counts.csv'
waterfall = ART / 'prediction_singapore_waterfall.png'
waterfall_dev = ART / 'prediction_singapore_waterfall_deviation.png'

if not pred_full.exists():
    raise SystemExit(f'Missing predictions file: {pred_full}')

df = pd.read_csv(pred_full)

# --- Filter predictions to drivers active in the 2025 season (if race results present) ---
rr_file = ROOT / 'race_results_2023_2024_2025.csv'
if rr_file.exists():
    try:
        rr = pd.read_csv(rr_file, dtype=str)
        if 'Season' in rr.columns:
            mask2025 = rr['Season'].astype(str) == '2025'
            drivers2025_id = set(rr.loc[mask2025, 'DriverId'].dropna().astype(str).str.strip())
            drivers2025_name = set(rr.loc[mask2025, 'FullName'].dropna().astype(str).str.strip())
            if drivers2025_id or drivers2025_name:
                def _is_active(row):
                    did = str(row.get('DriverId', '')).strip()
                    name = str(row.get('FullName', '')).strip()
                    return (did in drivers2025_id) or (name in drivers2025_name)
                before = len(df)
                df = df[df.apply(_is_active, axis=1)].reset_index(drop=True)
                after = len(df)
                print(f'Filtered predictions to 2025 drivers: {before} -> {after} rows')
            else:
                print('Warning: no 2025 drivers found in race_results_2023_2024_2025.csv; leaving predictions unchanged')
        else:
            print('Warning: race_results CSV missing Season column; skipping active-driver filter')
    except Exception as _e:
        print('Warning: failed to apply 2025 filter to predictions:', _e)

# Ensure prediction column exists
if 'prediction' not in df.columns:
    raise SystemExit('prediction column missing in prediction_singapore_full.csv')

# compute gap-from-winner (seconds behind predicted winner)
df = df.copy()
df['prediction'] = pd.to_numeric(df['prediction'], errors='coerce')
pred_min = df['prediction'].min()
df['SecondsBehindPredWinner_s'] = df['prediction'] - pred_min

# sort by predicted finishing order (ascending prediction -> fastest)
df_sorted = df.sort_values('prediction', ascending=True).reset_index(drop=True)

# dominant tyre from tyre_counts file if present
dominant_tyre = None
if tyre_counts.exists():
    try:
        tc = pd.read_csv(tyre_counts)
        if 'Compound' in tc.columns and 'Count' in tc.columns:
            dominant_tyre = tc.sort_values('Count', ascending=False).iloc[0]['Compound']
    except Exception:
        dominant_tyre = None

# detect per-driver compound if encoded in one-hot cols or explicit column
tyre_cols = ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']
def detect_compound(row):
    # prefer an explicit Compound-like column
    for cand in ['Compound', 'PredictedCompound', 'StartCompound']:
        if cand in row.index and pd.notna(row[cand]):
            return str(row[cand])
    # otherwise check binary columns
    for c in tyre_cols:
        if c in row.index:
            try:
                v = row[c]
                if (pd.notna(v) and int(float(v)) == 1):
                    return c
            except Exception:
                # non-numeric (e.g., True/False)
                if str(v).lower() in ('true','1','yes'):
                    return c
    return ''

df_sorted['PredictedCompound'] = df_sorted.apply(detect_compound, axis=1)

# ensure there's a driver display column
if 'Driver' not in df_sorted.columns:
    if 'FullName' in df_sorted.columns:
        df_sorted['Driver'] = df_sorted['FullName']
    elif 'BroadcastName' in df_sorted.columns:
        df_sorted['Driver'] = df_sorted['BroadcastName']
    elif 'Abbreviation' in df_sorted.columns:
        df_sorted['Driver'] = df_sorted['Abbreviation']
    else:
        # fallback to DriverId or empty
        df_sorted['Driver'] = df_sorted.get('DriverId', '')

# inline logo helper (used in the table per-row)
logo_base = ROOT / 'assets' / 'logos'
def inline_logo_for_team(team_name, height=22):
    if not team_name or pd.isna(team_name):
        return ''
    # find a matching logo file (prefer .png, fall back to .svg)
    safe = ''.join([ch for ch in str(team_name) if ch.isalnum() or ch in (' ','-')]).replace(' ','_')
    candidates = [logo_base / (safe + ext) for ext in ('.png', '.PNG', '.svg', '.SVG')]
    fname = None
    for p in candidates:
        if p.exists():
            fname = p
            break
    if fname is None:
        return ''
    try:
        data = fname.read_bytes()
        b64 = base64.b64encode(data).decode('ascii')
        if fname.suffix.lower() == '.svg':
            mime = 'image/svg+xml'
        else:
            mime = 'image/png'
        return f'<img src="data:{mime};base64,{b64}" style="height:{height}px;vertical-align:middle;margin-right:6px">'
    except Exception:
        return ''

# weather summary: look for columns in df like AirTemp_C, TrackTemp_C, Humidity_%
weather_keys = ['AirTemp_C', 'TrackTemp_C', 'Humidity_%', 'Pressure_hPa', 'WindSpeed_mps', 'WindDirection_deg']
weather = {k: (df_sorted[k].iloc[0] if k in df_sorted.columns else None) for k in weather_keys}

def make_table_html(df_in, nrows=999):
    # keep a concise set of columns if available
    cols = [c for c in ['GridPosition','Driver','DriverNumber','TeamName','prediction','PredictedCompound','SecondsBehindPredWinner_s'] if c in df_in.columns]
    out = ['<table border="1" cellspacing="0" cellpadding="6">']
    out.append('<thead><tr>')
    for c in cols:
        out.append(f'<th>{html.escape(c)}</th>')
    out.append('</tr></thead>')
    out.append('<tbody>')
    # first row is predicted winner (sorted ascending)
    for idx, r in df_in.head(nrows).iterrows():
        # highlight winner row
        tr_style = ''
        if idx == 0:
            tr_style = ' style="background:#e6ffe6;font-weight:700"'
        out.append(f'<tr{tr_style}>')
        for c in cols:
            val = r.get(c, '')
            if pd.isna(val):
                val = ''
            display_html = ''
            if c == 'TeamName':
                # inline logo + team name
                logo_html = inline_logo_for_team(val, height=20)
                display_html = f"{logo_html}{html.escape(str(val))}"
            else:
                if isinstance(val, float):
                    if c == 'prediction' or c == 'SecondsBehindPredWinner_s':
                        val = f'{val:.3f}'
                display_html = html.escape(str(val))
            out.append(f'<td>{display_html}</td>')
        out.append('</tr>')
    out.append('</tbody></table>')
    return '\n'.join(out)

html_parts = [
    '<!doctype html>',
    '<html lang="en">',
    '<head>',
    '<meta charset="utf-8">',
    '<title>Singapore GP Prediction Report</title>',
    '<style>body{font-family:Arial,Helvetica,sans-serif;margin:24px} h1{color:#2b2b2b} table{border-collapse:collapse} th{background:#f0f0f0}</style>',
    '</head>',
    '<body>',
    '<h1>Singapore GP — Prediction Report</h1>',
]

html_parts.append('<h2>Weather (input)</h2>')
html_parts.append('<ul>')
for k,v in weather.items():
    if v is None:
        continue
    html_parts.append(f'<li><strong>{html.escape(k)}</strong>: {html.escape(str(v))}</li>')
html_parts.append('</ul>')

if dominant_tyre:
    html_parts.append(f'<h2>Dominant predicted starting tyre: {html.escape(str(dominant_tyre))}</h2>')

html_parts.append('<h2>Waterfall: Seconds behind predicted winner</h2>')
if waterfall.exists():
    rel = Path('..') / 'artifacts' / waterfall.name
    # use the waterfall that already shows gap-from-winner if present; otherwise use dev image
    html_parts.append(f'<img src="{rel.as_posix()}" width="900">')
elif waterfall_dev.exists():
    rel = Path('..') / 'artifacts' / waterfall_dev.name
    html_parts.append(f'<img src="{rel.as_posix()}" width="900">')
else:
    html_parts.append('<p>No waterfall image found in artifacts/</p>')

html_parts.append('<h2>Predicted finishing order (top to bottom)</h2>')
html_parts.append(make_table_html(df_sorted))

# Inline team logos into a small summary above the table
logo_base = ROOT / 'assets' / 'logos'
def inline_logo_for_team(team_name):
    if not team_name or pd.isna(team_name):
        return ''
    # prefer png, then svg (case-insensitive)
    safe = ''.join([ch for ch in str(team_name) if ch.isalnum() or ch in (' ','-')]).replace(' ','_')
    candidates = [logo_base / (safe + ext) for ext in ('.png', '.PNG', '.svg', '.SVG')]
    fname = None
    for p in candidates:
        if p.exists():
            fname = p
            break
    if fname is None:
        return ''
    try:
        data = fname.read_bytes()
        b64 = base64.b64encode(data).decode('ascii')
        if fname.suffix.lower() == '.svg':
            mime = 'image/svg+xml'
        else:
            mime = 'image/png'
        return f'<img src="data:{mime};base64,{b64}" style="height:28px;vertical-align:middle;margin-right:6px">'
    except Exception:
        return ''

# Winner display
winner_name = ''
if not df_sorted.empty and 'Driver' in df_sorted.columns:
    winner_name = str(df_sorted.iloc[0]['Driver'])
    winner_team = df_sorted.iloc[0].get('TeamName', '')
    winner_logo = inline_logo_for_team(winner_team)
    html_parts.insert(6, f'<h2>Predicted winner: {winner_logo} {html.escape(str(winner_name))} — {html.escape(str(winner_team))}</h2>')

html_parts.append('<h2>Notes</h2>')
html_parts.append('<p>Predictions are model DeviationFromAvg_s values converted to seconds-behind-predicted-winner by subtracting the minimum predicted DeviationFromAvg_s.</p>')
html_parts.append('<p>"Seconds behind predicted winner" is non-negative; lower values are better.</p>')

html_parts.append('</body></html>')

out_file = OUT / 'prediction_singapore_report.html'
with open(out_file, 'w') as fh:
    fh.write('\n'.join(html_parts))

print('Wrote report to', out_file)
