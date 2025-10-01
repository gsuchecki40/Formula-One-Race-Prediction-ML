Artifacts README

This folder contains model artifacts and diagnostic outputs produced by the training pipeline.

Important files used for scoring:

Quick scoring example (from project root):
Artifacts folder

This folder holds trained models, preprocessing pipelines, SHAP outputs and diagnostic plots.

Key items
- `preprocessing_pipeline.joblib` — transformer that converts raw rows into model features.
- `ensemble_fold_models/` — per-fold models (averaged by `score_model.py` when present).
- `xgb_minimal_cv_randomized.joblib` — fallback single model used by scorer if no ensemble is found.
- `linear_calibration.joblib` — optional linear calibration applied to averaged predictions.
The input CSV should contain the same raw columns that were used to build `premodel_canonical.csv` (Season, Round, DriverId, GridPosition, etc.). The `preprocessing_pipeline.joblib` expects a pandas DataFrame with those columns.
Quick scoring example (from repo root):

```bash
python3 artifacts/score_model.py --input path/to/new_rows.csv --output artifacts/scored_preds.csv
```
If you want a self-contained Docker/virtualenv environment, install the pinned requirements in `requirements.txt`.
Input CSV
- The scorer expects the raw columns used when generating `premodel_canonical.csv` (GridPosition, AvgQualiTime, Rain, PointsProp, etc.). The scorer attempts reasonable fallbacks for partial inputs.

Copyright note
- Do not commit third-party race logos or copyrighted race reports into `artifacts/` or `presentation/`.
