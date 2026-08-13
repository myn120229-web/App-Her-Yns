"""
Scores a job 0-100 from five weighted parts, same breakdown the original
tool describes: required skills, preferred skills, keywords, meaning, and
your stated preferences. The model scores each part 0-100 with a short
reason; the weighted total is computed in plain Python afterwards so the
final number is never something the model just asserted.
"""
from __future__ import annotations

from app import llm_client

WEIGHTS = {
    "required_skills": 0.35,
    "preferred_skills": 0.20,
    "keywords": 0.15,
    "meaning": 0.15,
    "stated_preferences": 0.15,
}

SYSTEM_PROMPT = """You are a careful, skeptical job-fit assessor. You score how well a \
candidate's real, documented experience matches a job posting. You are not trying to be \
encouraging - you are trying to be accurate, because the candidate will waste real time \
applying to jobs you score too high.

Score five parts, each 0-100:
- required_skills: overlap between the candidate's knowledge base and the posting's \
REQUIRED / must-have skills. If the candidate has no evidence of a required skill, this \
must be low, even if other parts are strong.
- preferred_skills: overlap with NICE-TO-HAVE / preferred skills.
- keywords: overlap with the candidate's boosted keywords list, and absence of their \
penalty keywords.
- meaning: does the role/company domain match what the candidate says gives their work \
meaning?
- stated_preferences: does the role match the candidate's other stated preferences \
(team size, pace, remote posture, etc.)?

For each part, give a short reason (one sentence) and cite which knowledge-base item ids \
or job-posting phrases you're basing it on. Do not invent skills the candidate doesn't have.

Respond with ONLY this JSON shape, no prose outside it:
{
  "required_skills": {"score": 0-100, "reason": "...", "evidence": ["kb1", "..."]},
  "preferred_skills": {"score": 0-100, "reason": "...", "evidence": ["kb2", "..."]},
  "keywords": {"score": 0-100, "reason": "...", "evidence": ["..."]},
  "meaning": {"score": 0-100, "reason": "...", "evidence": ["..."]},
  "stated_preferences": {"score": 0-100, "reason": "...", "evidence": ["..."]}
}
"""


def _knowledge_base_text(profile: dict) -> str:
    lines = []
    for item in profile.get("knowledge_base", []):
        skills = ", ".join(item.get("skills", []))
        numbers = "; ".join(item.get("numbers", []))
        lines.append(
            f"- id={item['id']} | {item['title']}: {item['text']} | skills: {skills} | results: {numbers}"
        )
    return "\n".join(lines)


def _user_prompt(job: dict, profile: dict) -> str:
    prefs = profile.get("preferences", {})
    return f"""CANDIDATE KNOWLEDGE BASE:
{_knowledge_base_text(profile)}

CANDIDATE KEYWORD BOOSTS: {', '.join(prefs.get('keyword_boosts', []))}
CANDIDATE KEYWORD PENALTIES: {', '.join(prefs.get('keyword_penalties', []))}
CANDIDATE MEANING STATEMENT: {prefs.get('meaning_statement', '(none given)')}
CANDIDATE OTHER PREFERENCES: {prefs.get('other_preferences', '(none given)')}

JOB POSTING:
Title: {job.get('title')}
Company: {job.get('company')}
Location: {job.get('location')}
Description:
{job.get('description_text', '')[:4000]}

Score this job against this candidate now."""


def _clamp(v) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 0.0
    return max(0.0, min(100.0, v))


def score_job(job: dict, profile: dict) -> dict:
    result = llm_client.chat_json(
        SYSTEM_PROMPT,
        _user_prompt(job, profile),
        temperature=0.1,
    )
    breakdown = {}
    total = 0.0
    for key, weight in WEIGHTS.items():
        part = result.get(key, {}) if isinstance(result, dict) else {}
        score = _clamp(part.get("score", 0))
        breakdown[key] = {
            "score": score,
            "weight": weight,
            "weighted_points": round(score * weight, 1),
            "reason": part.get("reason", ""),
            "evidence": part.get("evidence", []),
        }
        total += score * weight

    return {
        "total_score": round(total, 1),
        "breakdown": breakdown,
    }
