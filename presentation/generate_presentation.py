#!/usr/bin/env python3
"""
Generate simple presentation assets: preds vs truth, residuals, and feature importance (if available)
"""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'
OUT = ROOT / 'presentation'
OUT.mkdir(exist_ok=True)

# load predictions and raw data
pred_file = ART / 'scored_preds_from_raw.csv'
raw_file = ROOT / 'premodeldatav1.csv'
if not pred_file.exists() or not raw_file.exists():
    print('predictions or raw file missing; run scorer first')
    raise SystemExit(1)

pred = pd.read_csv(pred_file)
raw = pd.read_csv(raw_file).reset_index()
merged = pred.merge(raw, left_on='index', right_on='index', how='left')
if 'DeviationFromAvg_s' in merged.columns:
    y = merged['DeviationFromAvg_s']
    yhat = merged['prediction']
    mask = ~y.isna()
    # preds vs truth
    plt.figure(figsize=(6,6))
    plt.scatter(y[mask], yhat[mask], alpha=0.6)
    plt.plot([y.min(), y.max()], [y.min(), y.max()], 'r--')
    plt.xlabel('True DeviationFromAvg_s')
    plt.ylabel('Predicted')
    plt.title('Predicted vs True')
    plt.savefig(OUT / 'preds_vs_true.png', bbox_inches='tight')
    plt.close()

    # residuals histogram
    res = (yhat - y)[mask]
    plt.figure(figsize=(6,4))
    plt.hist(res, bins=30)
    plt.xlabel('Residual (pred - true)')
    plt.title('Residuals')
    plt.savefig(OUT / 'residuals_hist.png', bbox_inches='tight')
    plt.close()

    # prediction histogram
    plt.figure(figsize=(6,4))
    plt.hist(yhat[mask], bins=30)
    plt.xlabel('Predicted DeviationFromAvg_s')
    plt.title('Prediction distribution')
    plt.savefig(OUT / 'prediction_hist.png', bbox_inches='tight')
    plt.close()

    # residual vs GridPosition scatter (if present)
    if 'GridPosition' in merged.columns:
        plt.figure(figsize=(8,4))
        plt.scatter(merged.loc[mask, 'GridPosition'], res, alpha=0.6)
        plt.xlabel('GridPosition')
        plt.ylabel('Residual (pred - true)')
        plt.title('Residual vs GridPosition')
        plt.savefig(OUT / 'residual_vs_grid.png', bbox_inches='tight')
        plt.close()

    # residuals by tyre compound boxplot (if tyre columns present)
    tyre_cols = ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']
    present_tyres = [c for c in tyre_cols if c in merged.columns]
    if present_tyres:
        # create a compound label column by picking the first tyre with value==1 else 'UNKNOWN'
        def pick_compound(row):
            for c in present_tyres:
                try:
                    if int(row[c]) == 1:
                        return c
                except Exception:
                    continue
            return 'UNKNOWN'
        df_tyres = merged.loc[mask, present_tyres + ['prediction', 'DeviationFromAvg_s']].copy()
        df_tyres['compound'] = df_tyres.apply(pick_compound, axis=1)
        df_tyres['residual'] = df_tyres['prediction'] - df_tyres['DeviationFromAvg_s']
        try:
            import seaborn as sns
            plt.figure(figsize=(8,4))
            sns.boxplot(x='compound', y='residual', data=df_tyres)
            plt.xlabel('Tyre compound')
            plt.ylabel('Residual (pred - true)')
            plt.title('Residuals by compound')
            plt.savefig(OUT / 'residuals_by_compound.png', bbox_inches='tight')
            plt.close()
        except Exception:
            # seaborn may not be available — skip gracefully
            pass

    # top-10 absolute errors table
    merged['abs_error'] = (merged['prediction'] - merged['DeviationFromAvg_s']).abs()
    top10 = merged.loc[mask].sort_values('abs_error', ascending=False).head(10)
    top_cols = [c for c in ['index', 'DriverNumber', 'GridPosition', 'prediction', 'DeviationFromAvg_s', 'abs_error'] if c in merged.columns]
    top10_html = top10[top_cols].to_html(index=False)

    # metrics summary (if available)
    metrics_unc = ART / 'metrics_scored_from_raw_uncalibrated.csv'
    metrics_cal = ART / 'metrics_scored_from_raw_calibrated.csv'
    metrics_html = ''
    if metrics_unc.exists() and metrics_cal.exists():
        try:
            m_unc = pd.read_csv(metrics_unc)
            m_cal = pd.read_csv(metrics_cal)
            metrics_html = '<h2>Metrics</h2>'
            metrics_html += '<h3>Uncalibrated</h3>' + m_unc.to_html(index=False)
            metrics_html += '<h3>Calibrated</h3>' + m_cal.to_html(index=False)
        except Exception:
            metrics_html = ''

# feature importance from saved shap summary if available
# look for any shap summary CSV and normalize column names (support mean_abs_shap)
shap_candidates = list(ART.glob('shap*_summary*.csv')) + list(ART.glob('shap*summary*.csv'))
shap_sum = None
if shap_candidates:
    # prefer ensemble summary if present
    prefer = ART / 'shap_remove_lapped_ensemble_summary.csv'
    if prefer in shap_candidates:
        shap_sum = prefer
    else:
        shap_sum = shap_candidates[0]

if shap_sum is not None and shap_sum.exists():
    sdf = pd.read_csv(shap_sum)
    # accept several common mean column names
    mean_cols = ['mean_abs', 'mean_abs_shap', 'mean_abs_shap', 'mean_abs_shap']
    mean_col = None
    for c in mean_cols:
        if c in sdf.columns:
            mean_col = c
            break
    if mean_col is None and len(sdf.columns) >= 2:
        # assume second column is the mean importance
        mean_col = sdf.columns[1]
    if 'feature' in sdf.columns and mean_col is not None:
        # normalize to feature & mean_abs
        df = sdf[['feature', mean_col]].rename(columns={mean_col: 'mean_abs'})
        df = df.sort_values('mean_abs', ascending=True)
        plt.figure(figsize=(6,8))
        plt.barh(df['feature'], df['mean_abs'])
        plt.xlabel('mean |SHAP|')
        plt.title('SHAP feature importance')
        plt.savefig(OUT / 'shap_feature_importance.png', bbox_inches='tight')
        plt.close()
    else:
        print('SHAP summary exists but lacks expected columns; skipping SHAP plot')

# create index.html (embed metrics and top-errors if available)
html_parts = [
    '<!doctype html>',
    '<html>',
    "<head><meta charset='utf-8'><title>Presentation</title></head>",
    '<body>',
    '<h1>Model Presentation</h1>'
]

if metrics_html:
    html_parts.append(metrics_html)

html_parts.append('<h2>Plots</h2>')
html_parts.append("<ul>")
html_parts.append("<li><img src='preds_vs_true.png' width='700'></li>")
html_parts.append("<li><img src='residuals_hist.png' width='700'></li>")
html_parts.append("<li><img src='prediction_hist.png' width='700'></li>")
html_parts.append("<li><img src='residual_vs_grid.png' width='700'></li>")
html_parts.append("<li><img src='residuals_by_compound.png' width='700'></li>")

# waterfall chart: predicted finishing order vs grid (positions gained/lost)
try:
    if 'GridPosition' in merged.columns and 'prediction' in merged.columns:
        # waterfall of predicted DeviationFromAvg_s ordered by GridPosition
        df_w = merged.loc[mask, ['DriverNumber', 'GridPosition', 'prediction', 'DeviationFromAvg_s']].copy()
        df_w = df_w.sort_values('GridPosition').reset_index(drop=True)
        # use prediction as predicted DeviationFromAvg_s
        values = df_w['prediction'].astype(float).fillna(0.0)
        colors = ['red' if v>0 else 'green' for v in values]
        plt.figure(figsize=(12,4))
        plt.bar(df_w['GridPosition'].astype(int).astype(str), values, color=colors)
        plt.axhline(0, color='k', linewidth=0.6)
        plt.xlabel('Grid Position')
        plt.ylabel('Predicted DeviationFromAvg_s')
        plt.title('Waterfall: Predicted DeviationFromAvg_s by Grid Position')
        plt.tight_layout()
        plt.savefig(OUT / 'waterfall_pred_result.png', bbox_inches='tight')
        plt.close()
        html_parts.append("<li><img src='waterfall_pred_result.png' width='900'></li>")
except Exception:
    # if anything fails, don't block the rest of the presentation
    pass

if (OUT / 'shap_feature_importance.png').exists():
    html_parts.append("<li><img src='shap_feature_importance.png' width='400'></li>")

# Team performance by weather
try:
    # choose a weather-like column if present
    weather_cols = ['Rain', 'Weather', 'weather_tire_cluster']
    weather_col = None
    for c in weather_cols:
        if c in merged.columns:
            weather_col = c
            break

    if 'TeamName' in merged.columns and weather_col is not None and 'prediction' in merged.columns:
        df_team = merged.loc[mask, ['TeamName', weather_col, 'prediction']].copy()
        df_team[weather_col] = df_team[weather_col].fillna('Unknown').astype(str)
        # aggregate
        agg = df_team.groupby(['TeamName', weather_col]).agg(mean_pred=('prediction','mean'), n=('prediction','count')).reset_index()

        # prepare x positions for weather categories
        weathers = sorted(agg[weather_col].unique())
        wx = {w:i for i,w in enumerate(weathers)}

        # color map for teams
        teams = sorted(agg['TeamName'].unique())
        cmap = plt.get_cmap('tab20')
        team_color = {t: cmap(i % 20) for i,t in enumerate(teams)}

        plt.figure(figsize=(10,6))
        ax = plt.gca()

        # helper to load logo if present
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox
        import os

        logo_base = ROOT / 'assets' / 'logos'

        for _, row in agg.iterrows():
            t = row['TeamName']
            w = row[weather_col]
            # deterministic jitter based on team name (stable across runs)
            sum_ord = sum([ord(c) for c in str(t)])
            jitter = ((sum_ord % 100) / 500.0) - 0.1
            x = wx[w] + jitter
            y = float(row['mean_pred'])
            size = max(40, min(300, int(row['n']) * 20))

            # try to load a logo image for the team (sanitized name)
            safe = ''.join([ch for ch in t if ch.isalnum() or ch in (' ','-')]).replace(' ','_')
            fname = logo_base / (safe + '.png')
            if fname.exists():
                try:
                    # scale zoom by sample count so larger samples show larger logos
                    zoom = 0.12 + min(0.8, float(row['n']) / 50.0)
                    img = OffsetImage(plt.imread(str(fname)), zoom=zoom)
                    ab = AnnotationBbox(img, (x,y), frameon=False)
                    ax.add_artist(ab)
                except Exception:
                    ax.scatter(x, y, s=size, color=team_color.get(t,'gray'), alpha=0.9, edgecolor='k')
            else:
                ax.scatter(x, y, s=size, color=team_color.get(t,'gray'), alpha=0.9, edgecolor='k')

            # annotate sample count next to each point
            try:
                ax.text(x + 0.03, y, f"n={int(row['n'])}", fontsize=8, alpha=0.8)
            except Exception:
                pass

        ax.set_xticks(list(wx.values()))
        ax.set_xticklabels(list(wx.keys()))
        ax.set_xlabel(weather_col)
        ax.set_ylabel('Mean predicted DeviationFromAvg_s')
        ax.set_title('Team performance by weather (prediction)')
        plt.tight_layout()
        outp = OUT / 'team_performance_by_weather.png'
        plt.savefig(outp, bbox_inches='tight')
        plt.close()
        html_parts.append("<li><img src='team_performance_by_weather.png' width='900'></li>")
except Exception:
    # non-fatal — skip if any issue
    pass
html_parts.append('</ul>')

if 'top10_html' in locals() and top10_html:
    html_parts.append('<h2>Top-10 absolute errors</h2>')
    html_parts.append(top10_html)

html_parts.append('</body>')
html_parts.append('</html>')

with open(OUT / 'index.html', 'w') as fh:
    fh.write('\n'.join(html_parts))
print('Wrote presentation assets to', OUT)
