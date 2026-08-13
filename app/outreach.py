"""
Builds targeted people-search links for a company (alumni-first, like the
original) and drafts a short opening message grounded in the knowledge
base. Nothing is scraped - these are just LinkedIn search URLs you open
and run yourself, so your account is never at risk, exactly like the tool
this is modeled on.
"""
from __future__ import annotations

import urllib.parse

from app import llm_client
from app.resume_writer import _extract_number_tokens, _number_is_traceable

ROLE_SEARCHES = [
    "recruiter",
    "engineering manager",
    "software engineer",
    "technical recruiter university",
    "engineering",
]

SYSTEM_PROMPT = """You draft a very short (2-3 sentence) cold outreach opening message from \
a candidate to someone at a company, to be sent on LinkedIn. Use only facts already present \
in the candidate's knowledge base - do not invent numbers, titles, or outcomes. Reference \
one concrete thing the candidate built. End with a light, low-pressure ask (e.g. asking for \
15 minutes, or asking about the team), not a hard pitch. No greetings like "Dear", keep it \
casual and short enough for a LinkedIn message box.

Respond with ONLY this JSON shape:
{"message": "...", "kb_id_used": "kb1", "project_suggestion": "one sentence describing a small project the candidate could build to stand out for this role, based on gaps between their knowledge base and the job"}
"""


def build_search_links(company_name: str, school: str | None = None) -> list[dict]:
    links = []
    company_q = urllib.parse.quote(company_name)
    for i, role in enumerate(ROLE_SEARCHES):
        keywords = f"{role} {company_name}"
        params = {"keywords": keywords, "origin": "GLOBAL_SEARCH_HEADER"}
        if school and i < 2:  # alumni-first: bias the first couple searches toward your school
            params["keywords"] = f"{role} {company_name} {school}"
        url = "https://www.linkedin.com/search/results/people/?" + urllib.parse.urlencode(params)
        links.append({
            "label": f"{role.title()} at {company_name}" + (" (alumni-weighted)" if school and i < 2 else ""),
            "url": url,
        })
    return links


def draft_outreach(profile: dict, job: dict) -> dict:
    kb = {i["id"]: i for i in profile.get("knowledge_base", [])}
    kb_text = "\n".join(
        f"- id={i['id']} | {i['title']}: {i['text']} | numbers: {i.get('numbers', [])}"
        for i in kb.values()
    )
    user_prompt = f"""KNOWLEDGE BASE:
{kb_text}

JOB:
Title: {job.get('title')}
Company: {job.get('company')}
Description: {job.get('description_text', '')[:2500]}

Draft the outreach message now."""

    warnings = []
    try:
        result = llm_client.chat_json(SYSTEM_PROMPT, user_prompt, temperature=0.4)
    except Exception as e:
        return {
            "message": None,
            "project_suggestion": None,
            "warnings": [f"Model call failed: {e}"],
        }

    message = (result.get("message") or "").strip()
    kb_id = result.get("kb_id_used")
    source_item = kb.get(kb_id)

    if message and source_item:
        bad_numbers = [t for t in _extract_number_tokens(message) if not _number_is_traceable(t, source_item)]
        if bad_numbers:
            warnings.append(f"Draft used untraceable number(s) {bad_numbers} - review before sending.")
    elif message and not source_item:
        warnings.append("Couldn't verify which knowledge-base item this message is based on - review before sending.")

    return {
        "message": message,
        "project_suggestion": result.get("project_suggestion", ""),
        "warnings": warnings,
    }


def find_contacts_and_pitch(profile: dict, job: dict) -> dict:
    links = build_search_links(job.get("company", ""), profile.get("school"))
    draft = draft_outreach(profile, job)
    return {"search_links": links, **draft}
