"""Preprocess `premodeldatav1.csv` and save a sklearn pipeline + transformed datasets.

Outputs (in `artifacts/`):
- preprocessing_pipeline.joblib
- X_train.csv, X_val.csv, X_test.csv
- columns_used.json

Assumptions:
- Time-based split by `Season`: train=2023, val=2024, test=2025 if those seasons exist.
- Drops identifier columns like `Unnamed: 0`, `FullName`, `HeadshotUrl`, `CountryCode`, `TeamColor`, `HeadshotUrl`.
- Numeric columns imputed with median, scaled with StandardScaler.
- Categorical columns imputed with constant 'missing' and OneHotEncoded (handle_unknown='ignore').
- The target is not created here; script only prepares features.
"""

import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# sklearn
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
import joblib

BASE = Path(__file__).resolve().parent
CSV = BASE / "premodeldatav1.csv"
ARTIFACTS = BASE / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

def detect_splits(df):
    seasons = sorted(df['Season'].dropna().unique())
    if set([2023,2024,2025]).issubset(set(seasons)):
        return 2023,2024,2025
    if len(seasons) >= 3:
        return seasons[-3], seasons[-2], seasons[-1]
    # fallback: 60/20/20 by ordering
    unique_rounds = df[['Season','Round']].drop_duplicates().reset_index(drop=True)
    cut1 = int(len(unique_rounds)*0.6)
    cut2 = int(len(unique_rounds)*0.8)
    train_rounds = unique_rounds.iloc[:cut1]
    val_rounds = unique_rounds.iloc[cut1:cut2]
    test_rounds = unique_rounds.iloc[cut2:]
    return train_rounds, val_rounds, test_rounds


def choose_columns(df):
    # drop obvious identifiers and large text
    drop_candidates = ['Unnamed: 0','FullName','HeadshotUrl','CountryCode','TeamColor','HeadshotUrl','DriverId']
    drop_cols = [c for c in drop_candidates if c in df.columns]
    # choose numeric and categorical
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    # include ParsedTime_s, FinishTime_s etc
    categorical = [c for c in df.columns if df[c].dtype == object and c not in drop_cols]
    # include Driver and TeamName as categorical features but guard cardinality
    for c in ['BroadcastName','Abbreviation','FirstName','LastName']:
        if c in categorical:
            categorical.remove(c)
    # keep Driver and TeamName if cardinality reasonable; otherwise drop to avoid huge one-hot expansion
    for col in ['Driver','TeamName']:
        if col in df.columns:
            nunique = df[col].nunique(dropna=True)
            if nunique <= 50:
                if col not in categorical:
                    categorical.append(col)
            else:
                if col in categorical:
                    categorical.remove(col)
    # Note: do not force 'Rain' into categorical here. The main() function
    # will coerce/encode the Rain column to a binary 0/1 integer before
    # column selection so it will appear in numeric if present.
    # remove AvgPitStopTime from features (it may be present)
    if 'AvgPitStopTime' in numeric:
        numeric.remove('AvgPitStopTime')
    return numeric, categorical, drop_cols


def main():
    print(f"Loading {CSV}")
    df = pd.read_csv(CSV)
    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())

    # Coerce Rain to a binary indicator (1 = rain, 0 = no rain).
    # Common values observed in the dataset: 'Rain' and 'NoRain'.
    # We'll handle a few textual variants conservatively.
    if 'Rain' in df.columns:
        def _map_rain(v):
            try:
                s = str(v).strip().lower()
            except Exception:
                return 0
            if s == '' or s in ('nan', 'none'):
                return 0
            # explicit negative forms -> 0
            if s.startswith('no') or s.startswith('n') and 'rain' not in s:
                return 0
            # if the token equals 'rain' or contains 'rain' (but not 'norain')
            if 'rain' in s and not s.startswith('no'):
                return 1
            return 0

        df['Rain'] = df['Rain'].apply(_map_rain).astype(int)

    # quick diagnostics
    print('\nDtypes:')
    print(df.dtypes.value_counts())
    print('\nMissing counts (top 20):')
    print(df.isna().sum().sort_values(ascending=False).head(20))

    # choose columns
    numeric, categorical, drop_cols = choose_columns(df)
    print(f"\nSelected {len(numeric)} numeric and {len(categorical)} categorical features. Dropping: {drop_cols}")

    # detect splits
    s_train, s_val, s_test = detect_splits(df)
    print(f"Using seasons splits: train={s_train}, val={s_val}, test={s_test}")

    train = df[df['Season'] == s_train].copy()
    val = df[df['Season'] == s_val].copy()
    test = df[df['Season'] == s_test].copy()

    # map very rare categorical values to 'OTHER' to avoid exploding one-hot columns
    category_mappings = {}
    if categorical:
        for col in categorical:
            # compute threshold: at least 1% of training rows or min 5
            thresh = max(5, int(len(train) * 0.01))
            counts = train[col].fillna('missing').value_counts()
            rare = counts[counts <= thresh].index.tolist()
            if rare:
                category_mappings[col] = rare
                train[col] = train[col].fillna('missing').apply(lambda x: x if x not in rare else 'OTHER')
                val[col] = val[col].fillna('missing').apply(lambda x: x if x not in rare else 'OTHER')
                test[col] = test[col].fillna('missing').apply(lambda x: x if x not in rare else 'OTHER')

    # persist mappings for future transform time
    if category_mappings:
        with open(ARTIFACTS / 'category_mappings.json', 'w') as f:
            json.dump(category_mappings, f, indent=2)

    # pipeline
    numeric_transformer = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    categorical_transformer = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        # use sparse_output for newer sklearn; fall back handled by environment
        # handle_unknown='ignore' ensures new teams/drivers at transform time won't break the pipeline
        ('ohe', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    preprocessor = ColumnTransformer([
        ('num', numeric_transformer, numeric),
        ('cat', categorical_transformer, categorical)
    ], remainder='drop')

    pipeline = Pipeline([
        ('preprocessor', preprocessor)
    ])

    print('Fitting pipeline on training data...')
    pipeline.fit(train)

    # transform and save
    X_train = pipeline.transform(train)
    X_val = pipeline.transform(val)
    X_test = pipeline.transform(test)

    # save feature names robustly
    # drop numeric columns that had no observed values in train (imputer would skip them)
    num_names = [c for c in numeric if train[c].notna().any()]
    ohe_names = []
    if categorical:
        ohe = pipeline.named_steps['preprocessor'].named_transformers_['cat'].named_steps['ohe']
        cats = ohe.categories_
        for col, cats_vals in zip(categorical, cats):
            for v in cats_vals:
                ohe_names.append(f"{col}__{v}")
    feature_names = num_names + ohe_names
    # if shapes still mismatch, try to retrieve names from the transformer (sklearn >=1.0)
    if X_train.shape[1] != len(feature_names):
        try:
            names = pipeline.named_steps['preprocessor'].get_feature_names_out()
            feature_names = list(names)
        except Exception:
            # final fallback: generic feature names matching produced shape
            feature_names = [f"f_{i}" for i in range(X_train.shape[1])]

    # save as CSVs
    pd.DataFrame(X_train, columns=feature_names).to_csv(ARTIFACTS / 'X_train.csv', index=False)
    pd.DataFrame(X_val, columns=feature_names).to_csv(ARTIFACTS / 'X_val.csv', index=False)
    pd.DataFrame(X_test, columns=feature_names).to_csv(ARTIFACTS / 'X_test.csv', index=False)

    # save any cardinality decisions for reference
    with open(ARTIFACTS / 'columns_used.json', 'w') as f:
        json.dump({'numeric': numeric, 'categorical': categorical, 'drop': drop_cols}, f, indent=2)

    joblib.dump(pipeline, ARTIFACTS / 'preprocessing_pipeline.joblib')

    print('Saved pipeline and transformed datasets to artifacts/')

if __name__ == '__main__':
    main()
