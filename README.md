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
gh repo create <owner>/<repo> --public --source=. --remote=origin --push
```

Option B: create repo on github.com and add remote:

```bash
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
```

3. After pushing, the `showcase` workflow will run on push and PRs for `main`/`master`. The workflow runs tests, executes `scripts/run_demo.py`, regenerates the `presentation/` folder and `artifacts/manifest.json`, and uploads `presentation/` as a workflow artifact.

4. To run the demo locally (recommended before pushing):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_pinned.txt
python3 scripts/run_demo.py
open presentation/index.html
```

If you want me to prepare a GitHub repo (create it and push), I can generate the exact git commands for you to run locally — but I can't push from here.
