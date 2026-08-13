"""
Pulls postings directly from the public JSON APIs that Greenhouse, Lever,
Ashby and SmartRecruiters expose for their customers' careers pages. No
scraping, no login, no API key - these are the same endpoints the careers
page itself calls in your browser.

Each fetch_* function returns a list of normalized job dicts:
{id, company, ats, title, location, url, description_text, posted_at}
"""
from __future__ import annotations

import re
import requests

TIMEOUT = 15
HEADERS = {"User-Agent": "unemployed-clone/1.0 (personal job search tool)"}


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_greenhouse(token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"greenhouse:{token}:{j['id']}",
            "company": token,
            "ats": "greenhouse",
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "description_text": _strip_html(j.get("content", "")),
            "posted_at": j.get("updated_at", ""),
        })
    return out


def fetch_lever(token: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for j in data:
        desc = j.get("descriptionPlain") or _strip_html(j.get("description", ""))
        lists = j.get("lists") or []
        for section in lists:
            desc += f"\n\n{section.get('text','')}\n" + _strip_html(section.get("content", ""))
        out.append({
            "id": f"lever:{token}:{j['id']}",
            "company": token,
            "ats": "lever",
            "title": j.get("text", ""),
            "location": (j.get("categories") or {}).get("location", ""),
            "url": j.get("hostedUrl", ""),
            "description_text": desc.strip(),
            "posted_at": str(j.get("createdAt", "")),
        })
    return out


def fetch_ashby(token: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"ashby:{token}:{j['id']}",
            "company": token,
            "ats": "ashby",
            "title": j.get("title", ""),
            "location": j.get("location", ""),
            "url": j.get("jobUrl", ""),
            "description_text": _strip_html(j.get("descriptionHtml", "")) or j.get("descriptionPlain", ""),
            "posted_at": j.get("publishedAt", ""),
        })
    return out


def fetch_smartrecruiters(token: str) -> list[dict]:
    base = f"https://api.smartrecruiters.com/v1/companies/{token}/postings"
    r = requests.get(base, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    out = []
    for j in data.get("content", []):
        posting_id = j["id"]
        title = j.get("name", "")
        location = j.get("location", {}).get("city", "")
        url = j.get("applyUrl") or f"https://jobs.smartrecruiters.com/{token}/{posting_id}"
        # Full description needs a second call per posting.
        desc = ""
        try:
            dr = requests.get(f"{base}/{posting_id}", headers=HEADERS, timeout=TIMEOUT)
            if dr.status_code == 200:
                jd = dr.json().get("jobAd", {}).get("sections", {})
                parts = []
                for section in jd.values():
                    parts.append(_strip_html(section.get("text", "")))
                desc = "\n\n".join(p for p in parts if p)
        except requests.RequestException:
            pass
        out.append({
            "id": f"smartrecruiters:{token}:{posting_id}",
            "company": token,
            "ats": "smartrecruiters",
            "title": title,
            "location": location,
            "url": url,
            "description_text": desc,
            "posted_at": j.get("releasedDate", ""),
        })
    return out


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
}


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def slugify_dashed(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def probe_company(name_or_token: str) -> list[dict]:
    """
    Try the given string (and a couple of slug variants) against all four
    ATS APIs. Returns a list of {ats, token, job_count} for every one that
    responded with real postings, so the UI can show "found on Greenhouse
    as 'stripe' (142 jobs)" and let the user confirm.
    """
    candidates = list(dict.fromkeys([
        name_or_token.strip(),
        slugify(name_or_token),
        slugify_dashed(name_or_token),
    ]))
    hits = []
    seen = set()
    for token in candidates:
        if not token:
            continue
        for ats, fn in FETCHERS.items():
            key = (ats, token)
            if key in seen:
                continue
            seen.add(key)
            try:
                jobs = fn(token)
                if jobs:
                    hits.append({"ats": ats, "token": token, "job_count": len(jobs)})
            except (requests.RequestException, ValueError, KeyError):
                continue
    return hits


def fetch_for_company(ats: str, token: str) -> list[dict]:
    fn = FETCHERS.get(ats)
    if not fn:
        raise ValueError(f"Unknown ATS: {ats}")
    return fn(token)
