#!/usr/bin/env python3
"""Generate a polished top-3 banner image using headshots from HeadshotUrl.

Reads:
- artifacts/prediction_singapore_full.csv (predictions)
- Processed_F1_Results.csv (contains HeadshotUrl keyed by FullName or DriverId)

Writes:
- artifacts/top3_headshots.png

This script is defensive: if a headshot cannot be downloaded it draws a placeholder with initials.
"""
import io
import os
import sys
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARTIFACTS = os.path.join(ROOT, 'artifacts')
os.makedirs(ARTIFACTS, exist_ok=True)


def fetch_image_bytes(url, timeout=6.0):
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Formula1Report/1.0)'
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def read_image_from_bytes(bts):
    try:
        img = Image.open(io.BytesIO(bts)).convert('RGBA')
        return img
    except Exception:
        return None


def make_placeholder(initials, size=512, bg_color='#dddddd', fg_color='#333333'):
    img = Image.new('RGBA', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    try:
        # try to load a system font
        font = ImageFont.truetype('Arial.ttf', int(size * 0.36))
    except Exception:
        font = ImageFont.load_default()
    w, h = draw.textsize(initials, font=font)
    draw.text(((size - w) / 2, (size - h) / 2), initials, font=font, fill=fg_color)
    return img


def circle_crop(pil_img, size=512):
    # Resize and center-crop using Pillow, then apply circular mask
    img = pil_img.convert('RGBA')
    w, h = img.size
    scale = size / max(w, h)
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # center crop to square
    left = max(0, (new_w - size) // 2)
    top = max(0, (new_h - size) // 2)
    img = img.crop((left, top, left + size, top + size))
    # circular mask
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    out = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    out.paste(img, (0, 0), mask=mask)
    return out


def initials_from_name(name):
    if not isinstance(name, str) or not name.strip():
        return '??'
    parts = name.split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def draw_flag_badge(base_img, country_code, size=64, margin=8):
    # Draw a small rectangle badge with country code (fallback to letters).
    badge_w = size
    badge_h = int(size * 0.6)
    badge = Image.new('RGBA', (badge_w, badge_h), (255, 255, 255, 220))
    d = ImageDraw.Draw(badge)
    try:
        font = ImageFont.truetype('Arial.ttf', int(badge_h * 0.5))
    except Exception:
        font = ImageFont.load_default()
    txt = (country_code or '').upper()[:3]
    w, h = d.textsize(txt, font=font)
    d.text(((badge_w - w) / 2, (badge_h - h) / 2), txt, fill='#111111', font=font)
    # paste badge onto bottom-right of base_img
    bw, bh = base_img.size
    pos = (bw - badge_w - margin, bh - badge_h - margin)
    base_img.paste(badge, pos, badge)
    return base_img


def main():
    pred_path = os.path.join(ARTIFACTS, 'prediction_singapore_full.csv')
    if not os.path.exists(pred_path):
        print('prediction file not found:', pred_path, file=sys.stderr)
        sys.exit(1)

    preds = pd.read_csv(pred_path)
    # compute SecondsBehindPredWinner_s if not present
    if 'SecondsBehindPredWinner_s' not in preds.columns:
        if 'prediction' in preds.columns:
            min_pred = preds['prediction'].min()
            preds['SecondsBehindPredWinner_s'] = preds['prediction'] - min_pred
        else:
            preds['SecondsBehindPredWinner_s'] = 0.0

    # choose top 3 by prediction (ascending -> fastest)
    top3 = preds.sort_values('prediction').head(3).copy()

    # try to load headshot mapping
    shot_map = {}
    candidates = [
        os.path.join(ROOT, 'Processed_F1_Results.csv'),
        os.path.join(ROOT, 'race_results_2023_2024_2025.csv'),
        os.path.join(ROOT, 'ALLMerged.csv')
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                df = pd.read_csv(c)
                if 'FullName' in df.columns and 'HeadshotUrl' in df.columns:
                    for _, r in df[['FullName', 'HeadshotUrl']].dropna().iterrows():
                        shot_map[str(r['FullName']).strip()] = r['HeadshotUrl']
            except Exception:
                pass

    images = []
    for _, r in top3.iterrows():
        full = r.get('FullName') or r.get('Driver')
        url = None
        if isinstance(full, str) and full.strip() in shot_map:
            url = shot_map[full.strip()]
        # sometimes DriverId or abbreviation is available
        if not url and 'DriverId' in r and pd.notna(r['DriverId']):
            url = shot_map.get(r['DriverId'])

        img = None
        if isinstance(url, str) and url.lower().startswith('http'):
            bts = fetch_image_bytes(url)
            if bts:
                img = read_image_from_bytes(bts)

        if img is None:
            initials = initials_from_name(full)
            img = make_placeholder(initials, size=512)
        # ensure RGB and size
        try:
            if img.dtype == np.float32 or img.dtype == np.float64:
                img = (img * 255).astype(np.uint8)
        except Exception:
            pass
        # circle crop to 300x300
        try:
            circ = circle_crop(img, size=300)
        except Exception:
            circ = img if img.shape[0] >= 300 else np.pad(img, ((0, max(0,300-img.shape[0])), (0,0), (0,0)))
        images.append((full, r.get('TeamName', ''), r.get('prediction'), r.get('predicted_start_tyre'), circ))

    # build figure
    fig_w = 9
    fig_h = 3
    fig, axes = plt.subplots(1, 3, figsize=(fig_w, fig_h))
    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
    for i, (name, team, pred, tyre, img) in enumerate(images):
        ax = axes[i]
        ax.imshow(img)
        ax.axis('off')
        # text below
        ax.text(0.5, -0.25, name, transform=ax.transAxes, ha='center', va='top', fontsize=12, weight='bold')
        ax.text(0.5, -0.42, team, transform=ax.transAxes, ha='center', va='top', fontsize=10, color='#555555')
        if pd.notna(pred):
            ax.text(0.5, -0.60, f'Pred: {pred:.3f}s — {tyre}', transform=ax.transAxes, ha='center', va='top', fontsize=10, color='#333333')

    plt.tight_layout()
    out_path = os.path.join(ARTIFACTS, 'top3_headshots.png')
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('Wrote top3 image to', out_path)


if __name__ == '__main__':
    main()
