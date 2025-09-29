<!--
PR template for the Formula1 model showcase.
When creating a PR that updates the model, presentation, or CI, use this template.
-->

# Showcase: Demo + Presentation

Summary
-------
Brief description of changes and why they should be included in the showcase.

What the CI will run
--------------------
- Install dependencies (uses `requirements_pinned.txt` if present)
- Run pytest
- Run `scripts/run_demo.py` to produce `presentation/` and `artifacts/manifest.json`
- Upload `presentation/` and `artifacts/manifest.json` as workflow artifacts
- On `main` branch pushes the `publish_presentation` workflow will publish `presentation/` to `gh-pages`

Checklist for reviewers
----------------------
- [ ] Tests pass in the Actions run
- [ ] The demo run completed successfully (see the Actions logs)
- [ ] `presentation/index.html` renders locally and contains expected plots
- [ ] `artifacts/manifest.json` exists and lists created artifacts
- [ ] If publishing to GitHub Pages, confirm the `gh-pages` branch was updated or the Pages site shows expected content

Notes / Deployment
------------------
If you need to modify the presentation generation or to change where artifacts are published, update `.github/workflows/publish_presentation.yml` and the demo script `scripts/run_demo.py` accordingly.

Optional: If this PR updates model artifacts (files under `artifacts/`), include a short note about model version, training date, and commit hash.
