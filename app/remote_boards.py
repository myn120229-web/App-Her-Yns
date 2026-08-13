"""
Pulls postings from public, documented remote-job-board feeds. Every
endpoint here is the board's own official free API or RSS feed - nothing
is scraped, nothing needs a login or paid proxy. This is how the tool
gets close to "LinkedIn-level" remote coverage without touching LinkedIn:
LinkedIn has no public jobs API for individual developers, and scraping
it (even via third-party "Apify actor" style tools) breaks their Terms
of Service and risks account/legal action - so it's deliberately not
attempted here.

Sources, each free + keyless:
- Remotive      https://remotive.com/api/remote-jobs
- Arbeitnow     https://www.arbeitnow.com/api/job-board-api
- RemoteOK      https://remoteok.com/api
- We Work Remotely  RSS feeds (per category)
- Jobicy        https://jobicy.com/api/v2/remote-jobs

All of these ask that you credit them + link back to the original
posting when you display their jobs, which the UI already does (every
job card links to job['url']).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

from app.ats_fetchers import _strip_html

TIMEOUT = 15
HEADERS = {"User-Agent": "unemployed-clone/1.0 (personal job search tool; contact: none)"}


def fetch_remotive(search: str = "") -> list[dict]:
    params = {"limit": 100}
    if search:
        params["search"] = search
    r = requests.get("https://remotive.com/api/remote-jobs", params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"remotive:{j['id']}",
            "company": j.get("company_name", ""),
            "ats": "remotive",
            "title": j.get("title", ""),
            "location": j.get("candidate_required_location", "Worldwide"),
            "url": j.get("url", ""),
            "description_text": _strip_html(j.get("description", "")),
            "posted_at": j.get("publication_date", ""),
        })
    return out


def fetch_arbeitnow(page: int = 1) -> list[dict]:
    r = requests.get("https://www.arbeitnow.com/api/job-board-api", params={"page": page}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for j in data.get("data", []):
        if not j.get("remote", True):
            continue  # arbeitnow includes some on-site EU roles too; skip those
        out.append({
            "id": f"arbeitnow:{j.get('slug', j.get('title',''))}",
            "company": j.get("company_name", ""),
            "ats": "arbeitnow",
            "title": j.get("title", ""),
            "location": j.get("location") or "Remote",
            "url": j.get("url", ""),
            "description_text": _strip_html(j.get("description", "")),
            "posted_at": str(j.get("created_at", "")),
        })
    return out


def fetch_remoteok(tag: str = "") -> list[dict]:
    url = "https://remoteok.com/api" + (f"?tag={tag}" if tag else "")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for j in data:
        if "id" not in j:  # first element is a legal/notice blob, not a job
            continue
        out.append({
            "id": f"remoteok:{j['id']}",
            "company": j.get("company", ""),
            "ats": "remoteok",
            "title": j.get("position", j.get("title", "")),
            "location": j.get("location") or "Worldwide",
            "url": j.get("url", f"https://remoteok.com/remote-jobs/{j['id']}"),
            "description_text": _strip_html(j.get("description", "")),
            "posted_at": j.get("date", ""),
        })
    return out


_WWR_CATEGORY_FEEDS = {
    "all": "https://weworkremotely.com/remote-jobs.rss",
    "full-stack": "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "back-end": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "front-end": "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    "devops": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "product": "https://weworkremotely.com/categories/remote-product-jobs.rss",
    "design": "https://weworkremotely.com/categories/remote-design-jobs.rss",
}


def fetch_weworkremotely(category: str = "all") -> list[dict]:
    url = _WWR_CATEGORY_FEEDS.get(category, _WWR_CATEGORY_FEEDS["all"])
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for item in root.findall(".//item"):
        title_raw = (item.findtext("title") or "").strip()
        company, _, role = title_raw.partition(": ")
        link = (item.findtext("link") or "").strip()
        desc = _strip_html(item.findtext("description") or "")
        pub_date = (item.findtext("pubDate") or "").strip()
        guid = (item.findtext("guid") or link or title_raw)
        out.append({
            "id": f"weworkremotely:{guid}",
            "company": company.strip() if role else "",
            "ats": "weworkremotely",
            "title": role.strip() if role else title_raw,
            "location": "Worldwide",
            "url": link,
            "description_text": desc,
            "posted_at": pub_date,
        })
    return out


def fetch_jobicy(tag: str = "", industry: str = "") -> list[dict]:
    params = {"count": 50}
    if tag:
        params["tag"] = tag
    if industry:
        params["industry"] = industry
    r = requests.get("https://jobicy.com/api/v2/remote-jobs", params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"jobicy:{j.get('id')}",
            "company": j.get("companyName", ""),
            "ats": "jobicy",
            "title": j.get("jobTitle", ""),
            "location": j.get("jobGeo") or "Worldwide",
            "url": j.get("url", ""),
            "description_text": _strip_html(j.get("jobDescription", "")) or j.get("jobExcerpt", ""),
            "posted_at": j.get("pubDate", ""),
        })
    return out


SOURCES = {
    "remotive": fetch_remotive,
    "arbeitnow": fetch_arbeitnow,
    "remoteok": fetch_remoteok,
    "weworkremotely": fetch_weworkremotely,
    "jobicy": fetch_jobicy,
}


def fetch_all(keyword: str = "") -> tuple[list[dict], list[str]]:
    """Fetches from every source, best-effort. Returns (jobs, errors) so
    one board being down doesn't stop the others."""
    all_jobs, errors = [], []
    try:
        all_jobs += fetch_remotive(search=keyword)
    except Exception as e:
        errors.append(f"Remotive: {e}")
    try:
        all_jobs += fetch_arbeitnow()
    except Exception as e:
        errors.append(f"Arbeitnow: {e}")
    try:
        all_jobs += fetch_remoteok(tag=keyword.split()[0] if keyword else "")
    except Exception as e:
        errors.append(f"RemoteOK: {e}")
    try:
        all_jobs += fetch_weworkremotely()
    except Exception as e:
        errors.append(f"We Work Remotely: {e}")
    try:
        all_jobs += fetch_jobicy(tag=keyword)
    except Exception as e:
        errors.append(f"Jobicy: {e}")
    return all_jobs, errors
