#!/usr/bin/env python3
"""Generate simple placeholder PNG logos for teams found in the dataset.

Creates files under assets/logos/<TeamName_sanitized>.png
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'
LOGO_DIR = ROOT / 'assets' / 'logos'
LOGO_DIR.mkdir(parents=True, exist_ok=True)

raw = ROOT / 'premodeldatav1.csv'
if not raw.exists():
    print('premodeldatav1.csv not found; cannot infer teams')
    raise SystemExit(1)

df = pd.read_csv(raw)
if 'TeamName' not in df.columns:
    print('No TeamName column found; nothing to do')
    raise SystemExit(0)

teams = sorted(df['TeamName'].dropna().unique())
cmap = plt.get_cmap('tab20')

def sanitize(name):
    return ''.join([c for c in name if c.isalnum() or c in (' ', '-')]).replace(' ', '_')

for i, t in enumerate(teams):
    color = cmap(i % 20)
    fig, ax = plt.subplots(figsize=(2,2))
    ax.add_patch(plt.Circle((0.5,0.5), 0.4, color=color))
    ax.text(0.5, 0.5, ''.join([w[0] for w in t.split()][:2]).upper(), ha='center', va='center', fontsize=20, color='white')
    ax.axis('off')
    out = LOGO_DIR / (sanitize(t) + '.png')
    fig.savefig(out, dpi=150, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    print('Wrote', out)
