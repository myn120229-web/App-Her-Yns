"""
Takes a LaTeX resume the user already has (their own template, their own
layout) and rewrites the wording of each \\item bullet to better match a
job, without touching the surrounding LaTeX structure. Anything it can't
verify against the knowledge base is left exactly as the user wrote it -
same "left exactly as you wrote it" guarantee as the plain-PDF resume.
"""
from __future__ import annotations

import re

from app import llm_client
from app.resume_writer import _extract_number_tokens

ITEM_LINE_RE = re.compile(r"^(\s*\\item(?:\[[^\]]*\])?\s*)(.*)$")

SYSTEM_PROMPT = """You improve individual LaTeX resume bullet lines so they better match a \
target job, using ONLY facts already present in the candidate's knowledge base. You are \
given the plain text of each bullet (LaTeX commands stripped) plus the candidate's \
knowledge base and a target job description.

Rules:
- Do not invent any number, metric, company, tool, or outcome not already present in the \
knowledge base.
- You may rephrase, reorder, and emphasize different real facts to match the job better.
- If a bullet has nothing meaningful to gain from rewriting, return it unchanged.
- Keep roughly the same length as the original.
- Do not include LaTeX commands, backslashes, or braces in your output - plain text only, \
they will be re-inserted into the template automatically.

Respond with ONLY this JSON shape:
{"rewrites": ["rewritten bullet 1 plain text", "rewritten bullet 2 plain text", ...]}
The list must have exactly as many entries, in the same order, as the bullets you were given.
"""


def _strip_latex(s: str) -> str:
    s = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+", "", s)
    s = s.replace("{", "").replace("}", "")
    return s.strip()


def extract_item_lines(latex_source: str) -> list[dict]:
    items = []
    for idx, raw_line in enumerate(latex_source.splitlines()):
        m = ITEM_LINE_RE.match(raw_line)
        if m:
            prefix, content = m.groups()
            plain = _strip_latex(content)
            if plain:
                items.append({"line_index": idx, "prefix": prefix, "original_content": content, "plain": plain})
    return items


def _kb_text(profile: dict) -> str:
    return "\n".join(
        f"- id={i['id']} | {i['title']}: {i['text']} | numbers: {i.get('numbers', [])}"
        for i in profile.get("knowledge_base", [])
    )


def _all_traceable_numbers(profile: dict) -> set[str]:
    nums = set()
    for i in profile.get("knowledge_base", []):
        for n in i.get("numbers", []):
            nums.update(_extract_number_tokens(n))
        nums.update(_extract_number_tokens(i.get("text", "")))
    return nums


def rewrite_latex(latex_source: str, profile: dict, job: dict | None = None) -> dict:
    items = extract_item_lines(latex_source)
    if not items:
        return {
            "latex": latex_source,
            "changed_count": 0,
            "warnings": ["No \\item lines found - this tool currently only rewrites itemize-style bullets."],
        }

    job_text = ""
    if job:
        job_text = f"\nTARGET JOB:\nTitle: {job.get('title')}\nCompany: {job.get('company')}\nDescription: {job.get('description_text','')[:3000]}\n"

    bullets_text = "\n".join(f"{n}. {it['plain']}" for n, it in enumerate(items))
    user_prompt = f"KNOWLEDGE BASE:\n{_kb_text(profile)}\n{job_text}\nBULLETS TO CONSIDER REWRITING:\n{bullets_text}"

    warnings = []
    try:
        result = llm_client.chat_json(SYSTEM_PROMPT, user_prompt, temperature=0.2)
        rewrites = result.get("rewrites", []) if isinstance(result, dict) else []
    except Exception as e:
        warnings.append(f"Model call failed ({e}); left every bullet exactly as written.")
        rewrites = []

    traceable_numbers = _all_traceable_numbers(profile)
    lines = latex_source.splitlines()
    changed_count = 0

    for i, item in enumerate(items):
        new_plain = rewrites[i].strip() if i < len(rewrites) else ""
        if not new_plain or new_plain == item["plain"]:
            continue
        bad_numbers = [t for t in _extract_number_tokens(new_plain) if t not in traceable_numbers]
        if bad_numbers:
            warnings.append(
                f"Left this line unchanged - rewrite used untraceable number(s) {bad_numbers}: "
                f"\"{item['plain'][:70]}...\""
            )
            continue
        # Re-escape a few LaTeX special characters before reinserting.
        escaped = (new_plain.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#"))
        lines[item["line_index"]] = f"{item['prefix']}{escaped}"
        changed_count += 1

    return {
        "latex": "\n".join(lines),
        "changed_count": changed_count,
        "total_bullets": len(items),
        "warnings": warnings,
    }
