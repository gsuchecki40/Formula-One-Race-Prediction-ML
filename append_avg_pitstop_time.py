#!/usr/bin/env python3
"""
Append average pit stop time per driver for each race to the race results CSV.

This script will:
 - detect the Season, Round and Driver columns in the CSV
 - for each unique (season, round) load the FastF1 race session once
 - compute the mean of session.laps['PitTime'] per driver when available
 - write a new column 'AvgPitStopTime' to the same CSV (overwrites if present)

Only the new column is added/modified — nothing else in the CSV is changed.

Run from the project root where the CSV lives:
    python append_avg_pitstop_time.py
"""
import os
import sys
import math
import pandas as pd
import numpy as np

try:
    import fastf1
except Exception as e:
    print("fastf1 is required. Install with: pip install fastf1")
    raise
import difflib
from tqdm import tqdm


CSV_PATH = "premodeldatav1.csv"
CACHE_DIR = "f1_cache"
AVG_COL = "AvgPitStopTime"


def detect_column(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def safe_int(x):
    try:
        return int(float(x))
    except Exception:
        return None


def main():
    # allow overriding CSV path via CLI
    csv_path = sys.argv[1] if len(sys.argv) > 1 else CSV_PATH

    if not os.path.exists(csv_path):
        print(f"CSV not found at {csv_path}. Run from project root or pass the path as the first arg.")
        sys.exit(1)

    # load
    df = pd.read_csv(csv_path)

    # detect columns
    season_col = detect_column(df, ["Season", "season", "Year", "year"])
    round_col = detect_column(df, ["Round", "RoundNumber", "round", "Round_No", "RoundNumber"])
    driver_col = detect_column(df, ["Driver", "BroadcastName", "Abbreviation", "DriverCode"])

    if season_col is None or round_col is None or driver_col is None:
        print("Could not detect required columns. Found columns:")
        print(df.columns.tolist())
        sys.exit(1)

    # ensure cache exists
    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)

    # Prepare output column
    if AVG_COL not in df.columns:
        df[AVG_COL] = np.nan

    # Build per-session mapping so we only load a session once
    sessions = df[[season_col, round_col]].drop_duplicates()

    # normalize names for mapping
    sessions = sessions.dropna()

    # iterate sessions
    for _, srow in tqdm(sessions.iterrows(), total=len(sessions), desc='Sessions'):
        season = safe_int(srow[season_col])
        rnd = safe_int(srow[round_col])
        if season is None or rnd is None:
            print(f"Skipping session with bad season/round: {srow.to_dict()}")
            continue

        mask = (df[season_col].astype(float) == float(season)) & (df[round_col].astype(float) == float(rnd))

        try:
            print(f"Loading session Season={season} Round={rnd} ...")
            session = fastf1.get_session(season, rnd, 'R')
            session.load()
            laps = session.laps
        except Exception as e:
            print(f"Could not load session Season={season} Round={rnd}: {e}")
            # leave values as NaN for this session
            continue

        # Build pit stop mapping. Prefer explicit PitTime when available.
        pit_map = {}

        # Helper to store mapping for several key formats (driver id, driver number)
        def store_keys(drv_key, drv_num, val):
            try:
                if drv_key is not None:
                    pit_map[str(drv_key).upper()] = float(val)
            except Exception:
                pass
            try:
                if drv_num is not None and not (pd.isna(drv_num)):
                    pit_map[str(int(drv_num))] = float(val)
            except Exception:
                pass

        if 'PitTime' in laps.columns and laps['PitTime'].notna().any():
            grouped = laps[laps['PitTime'].notna()].groupby('Driver')['PitTime'].mean()
            for drv, val in grouped.items():
                # store by Driver (usually string id) and by DriverNumber if present on rows
                # find a representative driver number for this driver id
                try:
                    rep = laps.loc[laps['Driver'] == drv, 'DriverNumber'].dropna().astype(int)
                    repnum = int(rep.iloc[0]) if len(rep) else None
                except Exception:
                    repnum = None
                store_keys(drv, repnum, val)

        else:
            # Try computing pit stop durations from PitInTime and PitOutTime
            if 'PitInTime' in laps.columns and 'PitOutTime' in laps.columns:
                try:
                    pit_df = laps[laps['PitInTime'].notna() & laps['PitOutTime'].notna()].copy()
                    # PitIn/Out may be timedelta or datetime-like. Handle both.
                    if pd.api.types.is_timedelta64_dtype(pit_df['PitInTime'].dtype) or pd.api.types.is_timedelta64_dtype(pit_df['PitOutTime'].dtype):
                        pit_df['StopSeconds'] = (pit_df['PitOutTime'] - pit_df['PitInTime']).dt.total_seconds()
                    else:
                        # convert to datetimes if not already
                        pit_df['PitInTime_dt'] = pd.to_datetime(pit_df['PitInTime'])
                        pit_df['PitOutTime_dt'] = pd.to_datetime(pit_df['PitOutTime'])
                        pit_df['StopSeconds'] = (pit_df['PitOutTime_dt'] - pit_df['PitInTime_dt']).dt.total_seconds()

                    if pit_df['StopSeconds'].notna().any():
                        # group by DriverNumber where possible, and by Driver
                        if 'DriverNumber' in pit_df.columns:
                            try:
                                gnum = pit_df.groupby('DriverNumber')['StopSeconds'].mean()
                                for drvnum, val in gnum.items():
                                    store_keys(None, drvnum, val)
                            except Exception:
                                pass
                        try:
                            g = pit_df.groupby('Driver')['StopSeconds'].mean()
                            for drv, val in g.items():
                                # representative driver number
                                try:
                                    rep = pit_df.loc[pit_df['Driver'] == drv, 'DriverNumber'].dropna().astype(int)
                                    repnum = int(rep.iloc[0]) if len(rep) else None
                                except Exception:
                                    repnum = None
                                store_keys(drv, repnum, val)
                        except Exception:
                            pass
                except Exception:
                    # ignore and continue to other fallbacks
                    pass

        # Fallback: sometimes pit stop info is stored in session.pit_stops (DataFrame-like)
        if not pit_map and hasattr(session, 'pit_stops'):
            try:
                pst = session.pit_stops
                if hasattr(pst, 'groupby'):
                    if 'StopTime' in pst.columns:
                        grouped = pst.groupby('Driver')['StopTime'].mean()
                        for drv, val in grouped.items():
                            # try to find driver number in pst
                            try:
                                rep = pst.loc[pst['Driver'] == drv, 'DriverNumber'].dropna().astype(int)
                                repnum = int(rep.iloc[0]) if len(rep) else None
                            except Exception:
                                repnum = None
                            store_keys(drv, repnum, val)
                    # sometimes column names differ
                    elif 'Duration' in pst.columns:
                        grouped = pst.groupby('Driver')['Duration'].mean()
                        for drv, val in grouped.items():
                            store_keys(drv, None, val)
            except Exception:
                pass

        # Now apply mapping to rows for this session
        # Prefer to match by DriverNumber column in CSV when available
        driver_number_col = detect_column(df, ['DriverNumber', 'driver_number', 'Number'])

        if driver_number_col is not None:
            # match via driver number first
            for idx in df.loc[mask].index:
                try:
                    drvnum = safe_int(df.at[idx, driver_number_col])
                    if drvnum is not None and str(int(drvnum)) in pit_map:
                        df.at[idx, AVG_COL] = pit_map[str(int(drvnum))]
                    else:
                        # fallback to name-based matching
                        val = str(df.at[idx, driver_col]) if driver_col in df.columns else ''
                        chosen = None
                        if val:
                            v_up = val.upper()
                            if v_up in pit_map:
                                chosen = pit_map[v_up]
                            else:
                                # fuzzy match against pit_map keys
                                keys = list(pit_map.keys())
                                matches = difflib.get_close_matches(v_up, keys, n=1, cutoff=0.6)
                                if matches:
                                    chosen = pit_map[matches[0]]
                        # if still not found, try fragments (first/last 3 chars)
                        if chosen is None and val:
                            v_up = val.upper()
                            frags = [v_up[:3], v_up[-3:]]
                            for f in frags:
                                if f in pit_map:
                                    chosen = pit_map[f]
                                    break
                        df.at[idx, AVG_COL] = chosen if chosen is not None else np.nan
                except Exception:
                    df.at[idx, AVG_COL] = np.nan
        else:
            # no driver number column, use name heuristics
            possible_driver_values = df.loc[mask, driver_col].fillna('').astype(str)
            for idx, drv_val in possible_driver_values.items():
                key = drv_val.strip()
                chosen = None
                if key:
                    key_upper = key.upper()
                    if key_upper in pit_map:
                        chosen = pit_map[key_upper]
                    else:
                        # try fragments
                        if len(key_upper) >= 3:
                            candidates = [key_upper, key_upper[:3], key_upper[-3:]]
                            for cand in candidates:
                                if cand in pit_map:
                                    chosen = pit_map[cand]
                                    break
                        # fuzzy match as fallback
                        if chosen is None:
                            matches = difflib.get_close_matches(key_upper, list(pit_map.keys()), n=1, cutoff=0.6)
                            if matches:
                                chosen = pit_map[matches[0]]
                        if chosen is None:
                            num = safe_int(key)
                            if num is not None and str(int(num)) in pit_map:
                                chosen = pit_map[str(int(num))]

                df.at[idx, AVG_COL] = chosen if chosen is not None else np.nan

        if not pit_map:
            print(f"Warning: no pit stop mapping found for Season={season} Round={rnd}")

    # report
    non_null = df[AVG_COL].notna().sum()
    total = len(df)
    print(f"Computed AvgPitStopTime for {non_null}/{total} rows ({non_null/total:.1%})")

    # backup original CSV before overwriting
    bak = csv_path + '.bak'
    try:
        if not os.path.exists(bak):
            os.rename(csv_path, bak)
            print(f"Backed up original CSV to {bak}")
        else:
            print(f"Backup already exists at {bak}; will overwrite CSV in place")
    except Exception:
        print("Could not create backup; writing in place")

    # save back (only modifies/creates AvgPitStopTime column)
    df.to_csv(csv_path, index=False)
    print(f"Done — appended column '{AVG_COL}' to {csv_path}")


if __name__ == '__main__':
    main()
