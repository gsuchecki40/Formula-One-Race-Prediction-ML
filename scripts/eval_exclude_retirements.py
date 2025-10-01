"""Small experiment: compare regressor trained on all rows vs trained after dropping retirements.

Usage: python scripts/eval_exclude_retirements.py
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.impute import SimpleImputer


def detect_retirement(df: pd.DataFrame) -> pd.Series:
    # Detect retirements by ClassifiedPosition starting with 'R' (user requested: remove the R's)
    if 'ClassifiedPosition' in df.columns:
        return df['ClassifiedPosition'].astype(str).str.upper().str.startswith('R')
    # fallback to Status-based detection if ClassifiedPosition not present
    status = df.get('Status')
    if status is not None:
        return status.astype(str).str.lower().str.contains('retir|rtd|dnf', na=False)
    return pd.Series(False, index=df.index)


def choose_target(df: pd.DataFrame) -> str:
    # prefer FinishTime_s if present
    if 'FinishTime_s' in df.columns:
        return 'FinishTime_s'
    # fallback: any numeric column with 'time' or ending with '_s'
    for c in df.columns:
        if ('time' in c.lower() or c.lower().endswith('_s')) and pd.api.types.is_numeric_dtype(df[c]):
            return c
    raise ValueError('No suitable numeric time target column found')


def run_experiment(csv_path: str | Path) -> dict:
    df = pd.read_csv(csv_path)
    # retirement mask on the raw CSV (before any target-based dropping)
    raw_ret_mask = detect_retirement(df)
    raw_ret_count = int(raw_ret_mask.sum())

    target = choose_target(df)

    # helper: evaluate model on an input dataframe
    def eval_on_df(local_df: pd.DataFrame) -> dict:
        # numeric feature selection
        num_cols = local_df.select_dtypes(include=[np.number]).columns.tolist()
        if target in num_cols:
            num_cols.remove(target)
        for rm in ('Unnamed: 0', 'DriverId', 'Driver', 'FullName'):
            if rm in num_cols:
                num_cols.remove(rm)

        X = local_df[num_cols].copy()
        y = local_df[target].copy()
        mask_valid = y.notnull()
        X = X.loc[mask_valid]
        y = y.loc[mask_valid]

        # drop numeric columns with no observed values
        X = X.dropna(axis=1, how='all')
        imp = SimpleImputer(strategy='median')
        X_imp = pd.DataFrame(imp.fit_transform(X), columns=X.columns, index=X.index)

        # train/eval
        if len(y) < 10:
            return {'n_rows': int(len(y)), 'rmse': None, 'mae': None}
        X_tr, X_te, y_tr, y_te = train_test_split(X_imp, y, test_size=0.25, random_state=42)
        m = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=2)
        m.fit(X_tr, y_tr)
        pred = m.predict(X_te)
        return {
            'n_rows': int(len(y)),
            'rmse': float(np.sqrt(mean_squared_error(y_te, pred))),
            'mae': float(mean_absolute_error(y_te, pred)),
            'test_index_count': int(len(y_te)),
        }

    results: dict = {}
    results['raw_total_rows'] = int(len(df))
    results['raw_retirements'] = raw_ret_count

    # Baseline: evaluate on the raw dataframe (we'll drop rows without target inside eval_on_df)
    baseline = eval_on_df(df)
    results['baseline_n_rows'] = baseline['n_rows']
    results['baseline_rmse_all'] = baseline['rmse']
    results['baseline_mae_all'] = baseline['mae']

    # Filtered: drop rows with ClassifiedPosition starting with 'R' BEFORE any target-based filtering
    df_filtered = df.loc[~raw_ret_mask].copy()
    filtered = eval_on_df(df_filtered)
    results['filtered_n_rows'] = filtered['n_rows']
    results['filtered_rmse'] = filtered['rmse']
    results['filtered_mae'] = filtered['mae']

    # Also report how many retirements remained after target-based filtering for baseline
    # (i.e. retirements that had a valid target and thus were in baseline rows)
    target = choose_target(df)
    baseline_target_mask = df[target].notnull()
    retirements_with_target = int((raw_ret_mask & baseline_target_mask).sum())
    results['retirements_with_target'] = retirements_with_target

    return results


def main():
    here = Path(__file__).resolve().parent.parent
    csv_path = here / 'premodeldatav1.csv'
    out = run_experiment(csv_path)
    print(json.dumps(out, indent=2))
    # save
    out_path = here / 'artifacts' / 'ab_exclude_retirements.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
