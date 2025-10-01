# Formula1 Qualifying Model

Small project for preprocessing, training, scoring and presenting a Formula1 qualifying model.

## Quick tasks

- Run unit tests:

  ```bash
  python3 -m pytest -q
  ```

- Run scorer on a raw CSV and write outputs to `artifacts/`:

  ```bash
  python3 scripts/run_score_and_metrics.py --input premodeldatav1.csv
  ```

- Regenerate presentation (after scoring):

  ```bash
  python3 presentation/generate_presentation.py
  open presentation/index.html
  ```

- Start the FastAPI scoring app locally (requires dependencies):

  ```bash
  pip install -r requirements_pinned.txt
  uvicorn serve.app:app --reload --port 8000
  ```

## Docker (simple)

 - Build image:

   ```bash
   docker build -t f1-scorer:latest .
   ```

 - Run container (exposes port 8000):

   ```bash
   docker run -p 8000:8000 f1-scorer:latest
   ```

Recommended: mount `artifacts/` into the container so you can update models without rebuilding:

```bash
docker run -p 8000:8000 -v $(pwd)/artifacts:/app/artifacts f1-scorer:latest
```

## Notes

- The scorer prefers the `artifacts/preprocessing_pipeline.joblib` and ensembles under `artifacts/ensemble_fold_models_remove_lapped/`.
- The scorer will attempt fallbacks (minimal numeric features) if the preprocessor cannot be applied to input rows; `Rain` tokens are normalized automatically.
- SHAP summary CSVs should contain `feature` and `mean_abs` columns for the presentation to include the SHAP plot.

## Model scoring helper

Run the scorer on a raw premodel CSV and write calibrated and uncalibrated predictions + metrics:

```bash
python3 scripts/run_score_and_metrics.py --input premodeldatav1.csv
```

This will call `artifacts/score_model.py` and produce the following under `artifacts/`:

- scored_preds_from_raw_uncalibrated.csv
- scored_preds_from_raw.csv (calibrated)
- metrics_scored_from_raw_uncalibrated.csv
- metrics_scored_from_raw_calibrated.csv

## Testing

- A pytest-compatible test suite is available under `tests/test_score_model.py`.
- To run tests (install pytest first if needed):

```bash
pip install pytest
python -m pytest -q
```

## Demo: how to run in future

1) CLI (batch scoring)

```bash
# Score a CSV and write artifacts
python3 scripts/run_score_and_metrics.py --input premodeldatav1.csv

# Predictions and metrics will be written to artifacts/
ls artifacts | grep scored_preds
```

2) Quick API demo with curl (assumes server running on localhost:8000)

```bash
# score an existing file path on the server host
curl -X POST -H "Content-Type: application/json" -d '{"input_csv":"/data/premodeldatav1.csv"}' http://localhost:8000/score

# Or upload a file and score it directly
curl -F "file=@premodeldatav1.csv" http://localhost:8000/upload_and_score
```

3) Docker (mount artifacts so you can swap models without rebuilding)

```bash
docker run -p 8000:8000 -v $(pwd)/artifacts:/app/artifacts f1-scorer:latest

# check health
curl http://localhost:8000/health
curl http://localhost:8000/version
```

If you'd like, I can add a small Makefile to bundle these commands.

## Caches & Artifacts (where to store large files)

Small, reproducible projects work best when large, regenerable caches are kept out of Git history. This repo follows that pattern:

- Keep FastF1 / session caches and the HTTP SQLite cache locally under `f1_cache/` (this directory is ignored by git in `.gitignore`).
- Do not commit `f1_cache/` or any `*.ff1pkl` / `*.sqlite` files — they are large and can break pushes. Instead keep them locally or store them in a separate archive.

Recommended workflows:

1. Local caching (fast development)
  - Let scripts write their caches to `./f1_cache/` (this is already the default for FastF1 in many helpers). The `f1_cache/` directory is excluded from the repository so it will stay on your machine only.

2. Reproducible artifacts (models, reports)
  - Model artifacts (joblib / xgb json files) and presentation outputs are kept under `artifacts/` and `presentation/`. If you want a lighter repo, move large model files out of the repo and host them as release assets or in an object store (S3/GCS) and document download steps below.

3. Sharing large caches or models
  - Option A (recommended for sharing): Upload model tarballs or caches to a release on GitHub or to cloud storage and add a short download script `scripts/fetch_models.sh` (not added by default).
  - Option B: Use Git LFS for versioning large binaries. If you choose LFS, track patterns such as `artifacts/*.joblib`, `*.ff1pkl`, and `*.sqlite` and be mindful of any storage quotas.

How to reproduce the presentation and artifacts

1. Make sure you have model artifacts available in `artifacts/` (either by running training locally or by downloading release assets):

  ```bash
  # If you keep models locally, ensure artifacts/ contains the preprocessing pipeline and models
  ls artifacts | head -n 20
  ```

2. Run the scorer to generate scored CSVs:

  ```bash
  python3 scripts/run_score_and_metrics.py --input premodeldatav1.csv
  ```

3. Regenerate the presentation HTML and images (uses the outputs from `artifacts/`):

  ```bash
  python3 presentation/generate_presentation.py
  open presentation/index.html
  ```

4. If you need to rebuild models from raw sources, follow the scripts under `artifacts/` (for example, `artifacts/retrain_minimal_features.py`) — this will produce `artifacts/preprocessing_pipeline.joblib` and model files used by the scorer.

If you'd like, I can add a small `scripts/fetch_models.sh` that downloads a release zip or cloud-hosted models and places them under `artifacts/`.

## Pushing this repo to GitHub (suggested)

If you'd like to publish this project to GitHub and show the demo in CI, follow these steps from the repo root (macOS zsh):

1. Initialize git, add files and commit:

```bash
git init
git add .
git commit -m "Initial import: Formula1 scorer + demo"
```

2. Create GitHub repo (replace <OWNER/REPO> with your repo). Option A: use GitHub CLI:

```bash
# Formula 1 Predictive Model

This repository contains scripts and artifacts for preprocessing, training, scoring and presenting a Formula 1 qualifying model.

Quick start
 - Run tests:
   ```bash
   python3 -m pytest -q
   ```

 - Score a CSV and write outputs to `artifacts/`:
   ```bash
   python3 scripts/run_score_and_metrics.py --input premodeldatav1.csv
   ```

 - Regenerate the presentation after scoring:
   ```bash
   python3 presentation/generate_presentation.py
   open presentation/index.html
   ```

 - Run the local scoring API (requires dependencies):
   ```bash
   pip install -r requirements_pinned.txt
   uvicorn serve.app:app --reload --port 8000
   ```

Docker
 - Build:
   ```bash
   docker build -t f1-scorer:latest .
   ```

 - Run (mount `artifacts/` so models/reports can be swapped):
   ```bash
   docker run -p 8000:8000 -v $(pwd)/artifacts:/app/artifacts f1-scorer:latest
   ```

Important notes
 - Do not commit copyrighted or third-party logos or images inside `presentation/` or `artifacts/`. Keep any copyrighted race reports or logos out of the repo. Presentation images that are safe to commit (logos you own or have rights to) can be added, but by default avoid committing large binary assets.
 - Model artifacts (joblib, xgb json) and generated reports are stored in `artifacts/` and `presentation/`. For a lightweight repo consider hosting large models as release assets or using Git LFS.
 - If you provide a raw CSV for scoring, the scorer expects the columns used in `premodel_canonical.csv` (GridPosition, AvgQualiTime, Rain, etc.). The scorer attempts fallbacks when inputs are partial.

Publishing to GitHub
 - You can push this repo to GitHub. If authentication is set up locally (SSH or gh CLI), the steps are:
   ```bash
   git remote add origin git@github.com:gsuchecki40/Formula-1-Predictive-Model.git
   git push -u origin main
   ```

What I can do next
 - Update README further or add a short CONTRIBUTING.md
 - Add a small script to download models (scripts/fetch_models.sh)
 - Help prepare a GitHub release with model artifacts (recommended for sharing large models)

If you want me to attempt to push this workspace to your GitHub remote I can try — I'll attempt a push and report any authentication errors and the exact commands you can run locally if needed.
