import subprocess
import sys
from pathlib import Path
import pandas as pd
import os


def make_test_input(path, rows=None):
    # rows: list of dicts to form the test CSV; fallback to a default sample
    if rows is None:
        rows = [
            {'DriverNumber': 1, 'GridPosition': 5, 'AvgQualiTime': 100.0, 'weather_tire_cluster': 1,
             'SOFT': 1, 'MEDIUM': 0, 'HARD': 0, 'INTERMEDIATE': 0, 'WET': 0,
             'races_prior_this_season': 3, 'Rain': 'NoRain', 'PointsProp': 0.1, 'Status': 'Finished', 'DeviationFromAvg_s': 12.0},
            {'DriverNumber': 2, 'GridPosition': 10, 'AvgQualiTime': 110.0, 'weather_tire_cluster': 0,
             'SOFT': 0, 'MEDIUM': 1, 'HARD': 0, 'INTERMEDIATE': 0, 'WET': 0,
             'races_prior_this_season': 5, 'Rain': 'Rain', 'PointsProp': 0.05, 'Status': 'Finished', 'DeviationFromAvg_s': 20.0},
            {'DriverNumber': 3, 'GridPosition': 15, 'AvgQualiTime': 120.0, 'weather_tire_cluster': 0,
             'SOFT': 0, 'MEDIUM': 0, 'HARD': 1, 'INTERMEDIATE': 0, 'WET': 0,
             'races_prior_this_season': 2, 'Rain': 'no rain', 'PointsProp': 0.0, 'Status': 'Lapped', 'DeviationFromAvg_s': 50.0}
        ]
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def run_scorer_and_assert(tmp_path, csv_path=None):
    repo_root = Path(__file__).resolve().parents[1]
    artifacts = repo_root / 'artifacts'
    if csv_path is None:
        csv_path = tmp_path / 'test_input.csv'
        make_test_input(csv_path)
    out_csv = tmp_path / 'out_preds.csv'
    cmd = [sys.executable, str(repo_root / 'artifacts' / 'score_model.py'), '--input', str(csv_path), '--output', str(out_csv)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    print(res.stderr)
    assert res.returncode == 0
    assert (artifacts / 'scored_preds_from_raw_uncalibrated.csv').exists()
    assert (artifacts / 'scored_preds_from_raw.csv').exists()
    # metrics files created when DeviationFromAvg_s present
    assert (artifacts / 'metrics_scored_from_raw_uncalibrated.csv').exists()
    assert (artifacts / 'metrics_scored_from_raw_calibrated.csv').exists()


def test_basic_run(tmp_path):
    run_scorer_and_assert(tmp_path)


def test_entirely_lapped_input(tmp_path):
    # All rows are Lapped -> scorer should drop them and exit gracefully (no exception), but produce no metrics
    rows = [
        {'DriverNumber': 1, 'GridPosition': 5, 'AvgQualiTime': 100.0, 'weather_tire_cluster': 1,
         'SOFT': 1, 'MEDIUM': 0, 'HARD': 0, 'INTERMEDIATE': 0, 'WET': 0,
         'races_prior_this_season': 3, 'Rain': 'NoRain', 'PointsProp': 0.1, 'Status': 'Lapped', 'DeviationFromAvg_s': 12.0},
        {'DriverNumber': 2, 'GridPosition': 10, 'AvgQualiTime': 110.0, 'weather_tire_cluster': 0,
         'SOFT': 0, 'MEDIUM': 1, 'HARD': 0, 'INTERMEDIATE': 0, 'WET': 0,
         'races_prior_this_season': 5, 'Rain': 'Rain', 'PointsProp': 0.05, 'Status': 'Lapped', 'DeviationFromAvg_s': 20.0}
    ]
    csv = tmp_path / 'all_lapped.csv'
    make_test_input(csv, rows=rows)
    # run scorer; it should not raise but will print a message and return
    repo_root = Path(__file__).resolve().parents[1]
    out_csv = tmp_path / 'out_lapped.csv'
    cmd = [sys.executable, str(repo_root / 'artifacts' / 'score_model.py'), '--input', str(csv), '--output', str(out_csv)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    # returncode 0 and outputs exist (though metrics may not be created because no rows to score)
    assert res.returncode == 0


def test_missing_pointsprop_and_unusual_rain(tmp_path):
    # missing PointsProp column, and unusual Rain tokens
    rows = [
        {'DriverNumber': 1, 'GridPosition': 5, 'AvgQualiTime': 100.0, 'weather_tire_cluster': 1,
         'SOFT': 1, 'MEDIUM': 0, 'HARD': 0, 'INTERMEDIATE': 0, 'WET': 0,
         'races_prior_this_season': 3, 'Rain': 'LightRain', 'Status': 'Finished', 'DeviationFromAvg_s': 12.0},
        {'DriverNumber': 2, 'GridPosition': 10, 'AvgQualiTime': 110.0, 'weather_tire_cluster': 0,
         'SOFT': 0, 'MEDIUM': 1, 'HARD': 0, 'INTERMEDIATE': 0, 'WET': 0,
         'races_prior_this_season': 5, 'Rain': 'HEAVY_RAIN', 'Status': 'Finished', 'DeviationFromAvg_s': 20.0}
    ]
    csv = tmp_path / 'missing_points_rain_tokens.csv'
    make_test_input(csv, rows=rows)
    run_scorer_and_assert(tmp_path, csv_path=csv)


def test_output_ranges_and_content(tmp_path):
    # validate that predictions are finite numbers and within a reasonable range
    repo_root = Path(__file__).resolve().parents[1]
    csv = tmp_path / 'test_input.csv'
    make_test_input(csv)
    out_csv = tmp_path / 'out_preds.csv'
    cmd = [sys.executable, str(repo_root / 'artifacts' / 'score_model.py'), '--input', str(csv), '--output', str(out_csv)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    artifacts = repo_root / 'artifacts'
    # read predictions the scorer wrote in artifacts (these are global), but ensure we only assert on the rows for our test run
    pred = pd.read_csv(artifacts / 'scored_preds_from_raw.csv')
    # predictions should be finite and not extreme
    assert pred['prediction'].apply(lambda v: pd.notna(v) and float('-1e6') < float(v) < float('1e6')).all()
    # check uncalibrated exists and has same length
    uncal = pd.read_csv(artifacts / 'scored_preds_from_raw_uncalibrated.csv')
    # The global artifacts may include previous runs; at minimum ensure uncalibrated has at least one row and match index column presence
    assert len(uncal) >= 1
    assert 'prediction' in uncal.columns and 'prediction' in pred.columns


def test_rain_token_normalization(tmp_path):
    # Ensure unusual rain tokens are normalized and do not cause imputer errors
    rows = [
        {'DriverNumber': 1, 'GridPosition': 5, 'AvgQualiTime': 100.0, 'weather_tire_cluster': 1,
         'SOFT': 1, 'MEDIUM': 0, 'HARD': 0, 'INTERMEDIATE': 0, 'WET': 0,
         'races_prior_this_season': 3, 'Rain': 'NoRain', 'PointsProp': 0.1, 'Status': 'Finished', 'DeviationFromAvg_s': 12.0},
        {'DriverNumber': 2, 'GridPosition': 10, 'AvgQualiTime': 110.0, 'weather_tire_cluster': 0,
         'SOFT': 0, 'MEDIUM': 1, 'HARD': 0, 'INTERMEDIATE': 0, 'WET': 0,
         'races_prior_this_season': 5, 'Rain': 'LightRain', 'PointsProp': 0.05, 'Status': 'Finished', 'DeviationFromAvg_s': 20.0}
    ]
    csv = tmp_path / 'rain_tokens.csv'
    df = pd.DataFrame(rows)
    df.to_csv(csv, index=False)
    # Run scorer - should succeed and produce metrics
    run_scorer_and_assert(tmp_path, csv_path=csv)


def test_regression_on_canonical_sample(tmp_path):
    """Run the scorer on a canonical small sample and assert RMSE is within an acceptable threshold.

    This provides a basic regression guard for future changes.
    """
    repo_root = Path(__file__).resolve().parents[1]
    fixture = repo_root / 'tests' / 'fixtures' / 'canonical_sample.csv'
    assert fixture.exists(), 'Canonical fixture missing'
    out_csv = tmp_path / 'out_canonical.csv'
    cmd = [sys.executable, str(repo_root / 'artifacts' / 'score_model.py'), '--input', str(fixture), '--output', str(out_csv)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    print(res.stderr)
    assert res.returncode == 0
    # read produced uncalibrated preds
    unc = pd.read_csv(repo_root / 'artifacts' / 'scored_preds_from_raw_uncalibrated.csv')
    # align by index with fixture
    preds = unc['prediction'].values
    truth = pd.read_csv(fixture)['DeviationFromAvg_s'].values
    from sklearn.metrics import mean_squared_error
    import math
    mse = mean_squared_error(truth, preds[: len(truth)])
    rmse = math.sqrt(mse)
    # threshold set conservatively (20s)
    assert rmse < 20.0, f'RMSE {rmse:.3f} exceeds threshold'
