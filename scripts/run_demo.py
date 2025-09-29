#!/usr/bin/env python3
"""Run a small demo: score canonical fixture, update manifest, generate presentation.

Usage: python3 scripts/run_demo.py
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'
FIX = ROOT / 'tests' / 'fixtures' / 'canonical_sample.csv'

def run(cmd):
    print('RUN:', ' '.join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        raise SystemExit(rc)

def main():
    if not FIX.exists():
        print('Fixture missing:', FIX)
        raise SystemExit(1)

    # score
    run([sys.executable, str(ART / 'score_model.py'), '--input', str(FIX), '--output', str(ART / 'scored_demo.csv')])

    # update manifest
    run([sys.executable, str(ART / 'update_manifest.py')])

    # generate presentation
    run([sys.executable, str(ROOT / 'presentation' / 'generate_presentation.py')])

    print('\nDemo complete. Presentation available at presentation/index.html and artifacts/manifest.json')

if __name__ == '__main__':
    main()
