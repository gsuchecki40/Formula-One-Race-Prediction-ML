Logo fetch workflow
===================

This folder includes a small helper to fetch real team logos and save them under `assets/logos/` so the HTML report embeds them inline.

Files
- `logo_urls_template.csv`: example CSV with `TeamName,URL` entries. Replace or extend with high-quality PNG logos.
- `download_team_logos.py`: downloader script. It sanitizes team names and saves files as `assets/logos/{sanitized}.png`.

Usage
1. Edit `presentation/logo_urls_template.csv`: replace the example URLs with authoritative PNG URLs for each team.
2. Run the downloader (dry-run first):

```bash
python3 presentation/download_team_logos.py --input presentation/logo_urls_template.csv --dry-run
```

3. If the mappings look correct, run the real download:

```bash
python3 presentation/download_team_logos.py --input presentation/logo_urls_template.csv
```

Security & ethics
- The script simply downloads URLs you provide. Ensure you have the right to use the images (public domain, Wikimedia Commons, or licensed sources).
- The script does not crawl sites or do heavy automated downloads; it waits between requests and supports a `--wait` parameter.

If you want, I can fetch a curated set of logos for you (from Wikimedia Commons or team media kits) — say the word and I'll proceed, or provide the URL list and I'll download them.
