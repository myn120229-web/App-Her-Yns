from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILE_PATH = DATA_DIR / "profile.json"
COMPANIES_PATH = DATA_DIR / "companies.json"
JOBS_PATH = DATA_DIR / "jobs.json"
EXAMPLE_PROFILE = Path(__file__).resolve().parent / "profile.example.json"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load(path: Path, default):
    _ensure_dir()
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data):
    _ensure_dir()
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


# ---------- profile (the knowledge base) ----------

def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        _ensure_dir()
        shutil.copy(EXAMPLE_PROFILE, PROFILE_PATH)
    return _load(PROFILE_PATH, {})


def save_profile(profile: dict):
    _save(PROFILE_PATH, profile)


# ---------- companies you're tracking ----------

def load_companies() -> list[dict]:
    return _load(COMPANIES_PATH, [])


def save_companies(companies: list[dict]):
    _save(COMPANIES_PATH, companies)


def add_company(company: dict):
    companies = load_companies()
    if any(c["token"] == company["token"] and c["ats"] == company["ats"] for c in companies):
        return
    companies.append(company)
    save_companies(companies)


def remove_company(token: str, ats: str):
    companies = [c for c in load_companies() if not (c["token"] == token and c["ats"] == ats)]
    save_companies(companies)


# ---------- jobs (fetched, filtered, scored) ----------

def load_jobs() -> dict:
    """dict keyed by job id -> job record"""
    return _load(JOBS_PATH, {})


def save_jobs(jobs: dict):
    _save(JOBS_PATH, jobs)


def upsert_jobs(new_jobs: list[dict]):
    jobs = load_jobs()
    for j in new_jobs:
        existing = jobs.get(j["id"], {})
        existing.update(j)
        jobs[j["id"]] = existing
    save_jobs(jobs)


def update_job(job_id: str, patch: dict):
    jobs = load_jobs()
    if job_id in jobs:
        jobs[job_id].update(patch)
        save_jobs(jobs)
