PY=python3
ART=artifacts

.PHONY: test manifest presentation score runapi

test:
	$(PY) -m pytest -q

manifest:
	$(PY) artifacts/update_manifest.py

presentation: manifest
	$(PY) presentation/generate_presentation.py

score:
	$(PY) scripts/run_score_and_metrics.py --input premodeldatav1.csv

runapi:
	# run the FastAPI app locally (requires requirements installed)
	uvicorn serve.app:app --reload --port 8000
