from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from pathlib import Path
import shutil
import subprocess
import sys
import json

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts'
app = FastAPI(title='Formula1 Scorer')

class ScoreRequest(BaseModel):
    input_csv: str


@app.post('/score')
async def score(req: ScoreRequest):
    inp = Path(req.input_csv)
    if not inp.exists():
        raise HTTPException(status_code=400, detail='input CSV not found')
    out = ART / 'scored_from_api.csv'
    cmd = [sys.executable, str(ART / 'score_model.py'), '--input', str(inp), '--output', str(out)]
    rc = subprocess.call(cmd)
    if rc != 0:
        raise HTTPException(status_code=500, detail='scoring failed')
    return {'predictions': str(out)}


@app.post('/upload_and_score')
async def upload_and_score(file: UploadFile = File(...)):
    tmp = Path('/tmp') / file.filename
    with open(tmp, 'wb') as fh:
        content = await file.read()
        fh.write(content)
    out = ART / ('scored_' + file.filename)
    cmd = [sys.executable, str(ART / 'score_model.py'), '--input', str(tmp), '--output', str(out)]
    rc = subprocess.call(cmd)
    if rc != 0:
        raise HTTPException(status_code=500, detail='scoring failed')
    return {'predictions': str(out)}




@app.get('/health')
async def health():
    # simple health check — ensure artifacts folder exists
    ok = ART.exists()
    resp = {'healthy': bool(ok)}
    manifest = ART / 'manifest.json'
    if manifest.exists():
        try:
            resp['manifest'] = json.loads(manifest.read_text())
        except Exception:
            resp['manifest'] = {'error': 'manifest unreadable'}
    return resp


@app.get('/version')
async def version():
    # minimal version info; could be extended to read git tag/commit
    out = {'app': 'formula1-scorer', 'version': '0.1'}
    manifest = ART / 'manifest.json'
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text())
            out['artifacts'] = list(data.get('items', {}).keys())[:20]
        except Exception:
            out['artifacts'] = []
    return out
