#!/usr/bin/env python3
"""Generate a waterfall chart for a single race (by Round) using model predictions.

Usage:
  python3 scripts/waterfall_for_round.py            # picks the first round found
  python3 scripts/waterfall_for_round.py --round 5  # pick Round==5
"""
from pathlib import Path
import argparse
import subprocess
import sys
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'
OUT = ROOT / 'presentation'
OUT.mkdir(exist_ok=True)

def ensure_predictions():
    pred_file = ART / 'scored_preds_from_raw.csv'
    # if not present, try to run scorer on the main premodel CSV
    if not pred_file.exists():
        print('scored_preds_from_raw.csv not found — running scorer on premodeldatav1.csv')
        cmd = [sys.executable, str(ART / 'score_model.py'), '--input', str(ROOT / 'premodeldatav1.csv'), '--output', str(ART / 'scored_preds_from_raw.csv')]
        rc = subprocess.call(cmd)
        if rc != 0:
            raise SystemExit('scoring failed')
    return pred_file


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--round', type=str, help='Round identifier to plot (matches values in raw file)')
    args = p.parse_args()

    pred_file = ensure_predictions()
    raw_file = ROOT / 'premodeldatav1.csv'
    if not raw_file.exists():
        raise SystemExit('raw premodeldatav1.csv missing')

    pred = pd.read_csv(pred_file)
    raw = pd.read_csv(raw_file).reset_index()
    merged = pred.merge(raw, left_on='index', right_on='index', how='left')

    if 'Round' in merged.columns:
        rounds = merged['Round'].dropna().unique().tolist()
    elif 'RoundNumber' in merged.columns:
        rounds = merged['RoundNumber'].dropna().unique().tolist()
    else:
        rounds = [None]

    if args.round:
        sel = args.round
        if sel not in [str(r) for r in rounds]:
            print('Requested round not found in data. Available rounds:', rounds)
            raise SystemExit(1)
    else:
        sel = str(rounds[0]) if rounds and rounds[0] is not None else None

    print('Selected round:', sel)
    if sel is None:
        raise SystemExit('No round information in raw data')

    df_round = merged[merged['Round'].astype(str) == str(sel)].copy()
    if df_round.empty:
        print('No rows for round', sel)
        raise SystemExit(1)

    # require GridPosition and prediction
    if 'GridPosition' not in df_round.columns:
        raise SystemExit('GridPosition column missing for selected round')

    # Use prediction as DeviationFromAvg_s proxy
    df_round['pred_dev'] = df_round['prediction'].astype(float)

    # order by predicted deviation (ranked: best/smallest first)
    df_round = df_round.sort_values('pred_dev', ascending=True).reset_index(drop=True)

    # prepare labels and colors
    # Build a disambiguated driver label: Name (#) - Team (if available)
    names = df_round.get('Driver', pd.Series(['']*len(df_round))).astype(str)
    numbers = df_round.get('DriverNumber', pd.Series(['']*len(df_round))).astype(str)
    teams = df_round.get('TeamName', pd.Series(['']*len(df_round))).astype(str)
    def make_label(nm, num, team):
        parts = []
        if nm and nm != 'nan':
            parts.append(nm)
        if num and num != 'nan':
            parts.append('#' + num)
        if team and team != 'nan':
            parts.append('-' + team)
        if parts:
            return ' '.join(parts)
        return num or nm
    driver_label = [make_label(nm, num, t) for nm, num, t in zip(names, numbers, teams)]
    grid_labels = df_round['GridPosition'].astype(int).astype(str)
    values = df_round['pred_dev'].values
    colors = ['red' if v>0 else 'green' for v in values]

    plt.figure(figsize=(14,5))
    bars = plt.bar(range(len(values)), values, color=colors)
    plt.axhline(0, color='k', linewidth=0.6)
    plt.xticks(range(len(values)), driver_label, rotation=45, ha='right')
    plt.xlabel('Driver')
    plt.ylabel('Predicted DeviationFromAvg_s')
    plt.title(f'Predicted DeviationFromAvg_s — Round {sel} (drivers ordered by prediction)')

    # annotate grid position above each bar
    for i, b in enumerate(bars):
        h = b.get_height()
        # place annotation slightly above the bar (or below if negative)
        if h >= 0:
            va = 'bottom'
            y = h + max(0.02, 0.01 * abs(h))
        else:
            va = 'top'
            y = h - max(0.02, 0.01 * abs(h))
        plt.text(b.get_x() + b.get_width()/2, y, f'Grid: {grid_labels.iloc[i]}', ha='center', va=va, fontsize=8, rotation=0)

    plt.tight_layout()
    outpng = OUT / f'waterfall_round_{sel}.png'
    plt.savefig(outpng, bbox_inches='tight')
    plt.close()

    print('Wrote', outpng)


if __name__ == '__main__':
    main()
