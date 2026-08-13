"""
unemployed — Telegram Mini App edition.

A FastAPI server that exposes the original app's logic (fetch / filter /
score / resume) over HTTP and serves a Mini App UI that talks to it.

Run:
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port $PORT

The Mini App UI is served at / and talks to the JSON API below.
The model endpoint is configurable at runtime via the UI (/api/config).
"""
from __future__ import annotations

import io
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import data_store, remote_boards, filters, scorer, resume_writer, llm_client

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
OUTPUT_DIR = BASE_DIR / "data" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="unemployed Mini App")

if PUBLIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = PUBLIC_DIR / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=500, detail="Mini App UI not found (public/index.html)")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ----------------------------------------------------------- profile
@app.get("/api/profile")
async def get_profile():
    return data_store.load_profile()


class ProfileIn(BaseModel):
    profile: dict


@app.post("/api/profile")
async def post_profile(body: ProfileIn):
    data_store.save_profile(body.profile)
    return {"success": True}


# ----------------------------------------------------------- pipeline
class SearchIn(BaseModel):
    keyword: str = ""


@app.post("/api/search")
async def search(body: SearchIn):
    jobs, errors = remote_boards.fetch_all(body.keyword)
    profile = data_store.load_profile()
    jobs = filters.filter_jobs(jobs, profile)
    # score only included jobs to save model calls
    for j in jobs:
        if j.get("included"):
            try:
                sc = scorer.score_job(j, profile)
                j["total_score"] = sc["total_score"]
                j["breakdown"] = sc["breakdown"]
            except Exception as e:
                j["total_score"] = None
                j["score_error"] = str(e)
    data_store.save_jobs({j["id"]: j for j in jobs})
    included = sorted([j for j in jobs if j.get("included")],
                      key=lambda x: x.get("total_score") or -1, reverse=True)
    return {"success": True, "count": len(included), "errors": errors, "jobs": included}


# ----------------------------------------------------------- resume
@app.get("/api/resume")
async def resume(job_id: str = Query(None)):
    profile = data_store.load_profile()
    job = None
    if job_id:
        job = data_store.load_jobs().get(job_id)
    result = resume_writer.generate_resume(profile, job, OUTPUT_DIR / "resume.pdf")
    bullets = [
        {"title": b["title"], "text": b["text"], "source": b["source"]}
        for b in result["bullets"]
    ]
    return {
        "success": True,
        "pdf": "/api/resume.pdf",
        "bullets": bullets,
        "warnings": result["warnings"],
    }


@app.get("/api/resume.pdf")
async def resume_pdf():
    path = OUTPUT_DIR / "resume.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run /api/resume first")
    return FileResponse(str(path), media_type="application/pdf", filename="resume.pdf")


# ----------------------------------------------------------- model config
@app.get("/api/config")
async def get_config():
    cfg = llm_client.get_config()
    # hide secret, show only last 4 chars of key
    masked = cfg["api_key"]
    if len(masked) > 4:
        masked = "****" + masked[-4:]
    return {"base_url": cfg["base_url"], "api_key_masked": masked, "model": cfg["model"]}


class ConfigIn(BaseModel):
    base_url: str
    api_key: str
    model: str


@app.post("/api/config")
async def set_config(body: ConfigIn):
    llm_client.set_config(body.base_url, body.api_key, body.model)
    return {"success": True, "config": llm_client.get_config()}


@app.get("/api/health")
async def health():
    return {"status": "ok", "model_available": llm_client.is_available()}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
