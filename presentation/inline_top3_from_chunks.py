#!/usr/bin/env python3
import re
from pathlib import Path

root = Path(__file__).parent
chunks_file = root / 'top3_datauri_chunks.txt'
html_file = root / 'prediction_singapore_report.html'

if not chunks_file.exists():
    raise SystemExit(f"missing {chunks_file}")
if not html_file.exists():
    raise SystemExit(f"missing {html_file}")

# Reassemble data URI
with chunks_file.open('r', encoding='utf-8') as f:
    lines = [ln.rstrip('\n') for ln in f]

# Some chunk files may include backticks or code fences if created incorrectly; drop them
clean_lines = [ln for ln in lines if not ln.strip().startswith('```')]
full = ''.join(clean_lines)

# Read HTML and replace the Top 3 image src
html = html_file.read_text(encoding='utf-8')

# We look for the img tag inside the Top 3 section that has the distinctive style attribute
pattern = re.compile(r'(<img\s+src=")[^"]*("\s+width="900"\s+style="border-radius:6px;box-shadow:0 6px 18px rgba\(0,0,0,0.12\)">)', re.DOTALL)

new_html, n = pattern.subn(r"\1" + full + r"\2", html, count=1)
if n == 0:
    # fallback: replace the first occurrence of the top3-local image reference
    pattern2 = re.compile(r'(<img\s+src=")[^"]*("\s+width="900"\s+style="border-radius:6px;box-shadow:0 6px 18px rgba\(0,0,0,0.12\)">)', re.DOTALL)
    new_html, n = pattern2.subn(r"\1" + full + r"\2", html, count=1)

if n == 0:
    raise SystemExit('failed to find target <img> tag to replace')

html_file.write_text(new_html, encoding='utf-8')
print(f'Updated {html_file} (replaced {n} img src)')
