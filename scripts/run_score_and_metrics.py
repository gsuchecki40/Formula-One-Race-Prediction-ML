#!/usr/bin/env python3
"""
Run scorer on an input CSV and print output file locations for predictions and metrics.
Usage:
  python3 scripts/run_score_and_metrics.py --input premodeldatav1.csv

This is a tiny helper to run the scorer and show where artifacts are saved.
"""
import argparse
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', default=str(ART / 'scored_preds_from_raw.csv'))
    args = ap.parse_args()
    cmd = [sys.executable, str(ART / 'score_model.py'), '--input', args.input, '--output', args.output]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        sys.exit(res.returncode)
    print('Wrote calibrated predictions to', args.output)
    print('Uncalibrated predictions:', ART / 'scored_preds_from_raw_uncalibrated.csv')
    print('Metrics (uncalibrated):', ART / 'metrics_scored_from_raw_uncalibrated.csv')
    print('Metrics (calibrated):', ART / 'metrics_scored_from_raw_calibrated.csv')
