#!/usr/bin/env python3
"""CLI wrapper for the artifacts scorer.
Usage:
  python3 cli/score_cli.py --input premodeldatav1.csv --output artifacts/scored_preds_from_raw.csv
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', default=str(ART / 'scored_preds_from_raw.csv'))
    ap.add_argument('--version', action='store_true')
    args = ap.parse_args()
    if args.version:
        print('Model artifacts:')
        for f in (ART).glob('*.joblib'):
            print(' -', f.name)
        sys.exit(0)
    cmd = [sys.executable, str(ART / 'score_model.py'), '--input', args.input, '--output', args.output]
    rc = subprocess.call(cmd)
    sys.exit(rc)
