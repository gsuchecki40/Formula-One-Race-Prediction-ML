Preprocessing for `premodeldatav1.csv`

Usage

1. Install dependencies (recommended in a virtualenv):

```bash
pip install -r requirements.txt
```

2. Run the preprocessing script (it will create `artifacts/`):

```bash
python preprocess_premodel.py
```

Outputs
- `artifacts/preprocessing_pipeline.joblib` - fitted sklearn pipeline
- `artifacts/X_train.csv`, `X_val.csv`, `X_test.csv` - transformed feature CSVs
- `artifacts/columns_used.json` - list of selected numeric and categorical columns

Notes
- Splits: defaults to seasons 2023/2024/2025 when available. Otherwise uses last three seasons or a 60/20/20 rounds-based split.
- The script drops obvious identifiers and prepares only features (no target handling).