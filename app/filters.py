"""
Filters jobs down to ones you could actually take, the same way the
original tool describes it: "Every exclusion carries the rule that caused
it, in plain words." Nothing here calls the model - it's all cheap regex
so it runs instantly on hundreds of postings before anything gets scored.
"""
from __future__ import annotations

import re

SENIORITY_LEVELS = ["Intern", "Junior", "Mid", "Senior", "Staff", "Principal", "Director", "VP", "Executive"]

_SENIORITY_PATTERNS = [
    (r"\bintern(ship)?\b", "Intern"),
    (r"\b(new grad|graduate|junior|jr\.?|entry.level|associate\b)", "Junior"),
    (r"\b(staff)\b", "Staff"),
    (r"\b(principal)\b", "Principal"),
    (r"\b(director|head of)\b", "Director"),
    (r"\b(vp|vice president)\b", "VP"),
    (r"\b(chief|cxo|cto\b|ceo\b|cfo\b)", "Executive"),
    (r"\b(sr\.?|senior|lead\b|iii\b|iv\b)", "Senior"),
]

# Phrases that mean "remote, but only within a region" - i.e. NOT worldwide-remote.
_RESTRICTED_REMOTE_HINTS = [
    "remote - us only", "remote (us only)", "us remote only", "must be based in the us",
    "must be located in the us", "remote - uk only", "remote (uk only)", "eu remote only",
    "must be authorized to work in", "must reside in", "candidates must be based in",
    "no visa sponsorship", "this role is not available outside",
]

# Phrases that indicate the role explicitly is NOT remote.
_ONSITE_HINTS = ["on-site only", "not a remote position", "no remote", "in-office", "hybrid required"]


def is_worldwide_remote(job: dict) -> tuple[bool, str | None]:
    """Best-effort check that a job is remote with no hard geographic
    restriction. Jobs pulled from dedicated remote-only boards (Remotive,
    Arbeitnow, RemoteOK, We Work Remotely, Jobicy) are remote by
    definition, so this mainly matters for ATS-sourced company postings."""
    text = f"{job.get('location','')} {job.get('description_text','')[:600]}".lower()
    source = job.get("ats", "")
    if source in ("remotive", "arbeitnow", "remoteok", "weworkremotely", "jobicy"):
        for hint in _RESTRICTED_REMOTE_HINTS:
            if hint in text:
                return False, f"listed on a remote board but text suggests a geo restriction: '{hint}'"
        return True, None

    if "remote" not in text:
        return False, "no mention of remote work in location or description"
    for hint in _ONSITE_HINTS:
        if hint in text:
            return False, f"says '{hint}' despite mentioning remote elsewhere"
    for hint in _RESTRICTED_REMOTE_HINTS:
        if hint in text:
            return False, f"remote but geo-restricted: '{hint}'"
    return True, None


def detect_seniority(title: str) -> str:
    t = title.lower()
    for pattern, level in _SENIORITY_PATTERNS:
        if re.search(pattern, t):
            return level
    return "Mid"  # no signal in the title = assume mid-level, the safe default


def detect_required_years(description: str) -> int | None:
    """Looks for the highest '<N>+ years' style requirement in the text."""
    matches = re.findall(
        r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?years?\s+(?:of\s+)?experience",
        description.lower(),
    )
    if not matches:
        return None
    return max(int(m) for m in matches)


def function_matches(title: str, description: str, target_functions: list[str], excluded_functions: list[str]) -> tuple[bool, str | None]:
    text = f"{title} {description[:400]}".lower()
    for excl in excluded_functions:
        if excl.lower() in title.lower():
            return False, f"title matches an excluded function: '{excl}'"
    if not target_functions:
        return True, None
    for fn in target_functions:
        words = fn.lower().split()
        if all(w in text for w in words) or fn.lower() in title.lower():
            return True, None
    return False, f"title/description don't mention any target function ({', '.join(target_functions)})"


SENIORITY_RANK = {lvl: i for i, lvl in enumerate(SENIORITY_LEVELS)}


def apply_filters(job: dict, profile: dict) -> dict:
    """Returns the job dict with 'included' (bool) and 'exclusion_reasons' (list[str]) set."""
    reasons = []

    title = job.get("title", "")
    description = job.get("description_text", "")

    # 1. Seniority ceiling
    ceiling = profile.get("seniority_ceiling", "Senior")
    detected = detect_seniority(title)
    job["detected_seniority"] = detected
    if ceiling in SENIORITY_RANK and SENIORITY_RANK.get(detected, 2) > SENIORITY_RANK[ceiling]:
        reasons.append(f"seniority: title reads as '{detected}', above your ceiling of '{ceiling}'")

    # 2. Years of experience required
    years_have = profile.get("years_experience", 0)
    years_req = detect_required_years(description)
    job["detected_years_required"] = years_req
    if years_req is not None and years_req > years_have + 1:  # +1 year of slack
        reasons.append(f"experience: asks for {years_req}+ years, you have {years_have}")

    # 3. Function / role match
    ok, why = function_matches(
        title, description,
        profile.get("target_functions", []),
        profile.get("excluded_functions", []),
    )
    if not ok:
        reasons.append(f"function: {why}")

    # 4. Worldwide remote only
    remote_ok, why_not_remote = is_worldwide_remote(job)
    if not remote_ok:
        reasons.append(f"not worldwide-remote: {why_not_remote}")

    # 5. Hard keyword penalties (e.g. "must be on-site", banned tech)
    penalties = profile.get("preferences", {}).get("keyword_penalties", [])
    hit_penalties = [p for p in penalties if p.lower() in description.lower()]
    if hit_penalties:
        reasons.append(f"dealbreaker keywords present: {', '.join(hit_penalties)}")

    job["exclusion_reasons"] = reasons
    job["included"] = len(reasons) == 0
    return job


def filter_jobs(jobs: list[dict], profile: dict) -> list[dict]:
    return [apply_filters(dict(job), profile) for job in jobs]
