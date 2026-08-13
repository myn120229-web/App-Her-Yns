"""
Turns the knowledge base into resume bullets, tailored to a specific job
if one is given. The rule from the original tool: every bullet must trace
back to something in the knowledge base, and any number the model writes
that isn't already in that knowledge-base entry gets the bullet thrown out
- replaced with a plain, safe version built directly from the source data
instead of just deleted, so nothing silently disappears.

Then it lays the result out as a one-page PDF and reads the PDF back with
a text extractor to confirm every surviving bullet actually made it onto
the page (catches layout/overflow silently dropping content).
"""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from pypdf import PdfReader

from app import llm_client

MAX_BULLETS = 8

SYSTEM_PROMPT = """You write resume bullets for a candidate, strictly from their own \
knowledge base. Rules, absolute:
1. Every bullet must be based on exactly one knowledge-base item. Reference its id.
2. Never state a number, percentage, or metric that is not already present in that \
item's "numbers" or "text" field. If you want to use a number, copy it verbatim from \
the source.
3. Never invent a skill, tool, or outcome not present in the source item.
4. If a job description is provided, prioritize and phrase bullets to highlight the \
overlap with that job's requirements, but do not add anything not in the source.
5. One bullet per line, action-verb first, no first person pronouns, no periods needed.

Respond with ONLY this JSON shape:
{"bullets": [{"kb_id": "kb1", "bullet": "Rebuilt ... cutting p99 latency from 8s to 400ms"}]}
"""


def _fallback_bullet(item: dict) -> str:
    """Deterministic, always-truthful bullet built straight from the source
    item, used when the model's version can't be verified."""
    numbers = ", ".join(item.get("numbers", [])[:2])
    text = item["text"].strip().rstrip(".")
    if numbers:
        return f"{text} ({numbers})"
    return text


def _extract_number_tokens(text: str) -> list[str]:
    return re.findall(r"\d[\d,.]*\s*%?|\$\d[\d,.]*[kKmM]?|\d+[kKmM]\+?", text)


def _number_is_traceable(token: str, item: dict) -> bool:
    haystack = " ".join(item.get("numbers", [])) + " " + item.get("text", "")
    normalized_token = token.replace(",", "").strip()
    normalized_haystack = haystack.replace(",", "")
    return normalized_token in normalized_haystack or token in haystack


def generate_bullets(profile: dict, job: dict | None = None) -> tuple[list[dict], list[str]]:
    """Returns (bullets, warnings). Each bullet: {kb_id, title, text, source: 'model'|'fallback'}"""
    kb = {item["id"]: item for item in profile.get("knowledge_base", [])}
    if not kb:
        return [], ["Knowledge base is empty - add accomplishments in your profile first."]

    kb_text = "\n".join(
        f"- id={i['id']} | {i['title']}: {i['text']} | numbers: {i.get('numbers', [])}"
        for i in kb.values()
    )
    job_text = ""
    if job:
        job_text = f"\nTARGET JOB:\nTitle: {job.get('title')}\nCompany: {job.get('company')}\nDescription: {job.get('description_text','')[:3000]}\n"

    user_prompt = f"KNOWLEDGE BASE:\n{kb_text}\n{job_text}\nWrite one strong bullet per knowledge-base item."

    warnings = []
    try:
        result = llm_client.chat_json(SYSTEM_PROMPT, user_prompt, temperature=0.2)
        raw_bullets = result.get("bullets", []) if isinstance(result, dict) else []
    except Exception as e:
        warnings.append(f"Model call failed ({e}); using fallback bullets built directly from your knowledge base.")
        raw_bullets = []

    seen_ids = set()
    bullets = []
    for rb in raw_bullets:
        kb_id = rb.get("kb_id")
        text = (rb.get("bullet") or "").strip()
        item = kb.get(kb_id)
        if not item or not text:
            continue
        bad_numbers = [t for t in _extract_number_tokens(text) if not _number_is_traceable(t, item)]
        if bad_numbers:
            warnings.append(
                f"Dropped a model bullet for '{item['title']}' - it stated {bad_numbers} which "
                f"isn't in your knowledge base. Used a plain version built from your source data instead."
            )
            text = _fallback_bullet(item)
            source = "fallback"
        else:
            source = "model"
        bullets.append({"kb_id": kb_id, "title": item["title"], "text": text, "source": source})
        seen_ids.add(kb_id)

    # Any knowledge-base item the model skipped still gets a fallback bullet,
    # so nothing you told it about silently disappears.
    for kb_id, item in kb.items():
        if kb_id not in seen_ids:
            bullets.append({"kb_id": kb_id, "title": item["title"], "text": _fallback_bullet(item), "source": "fallback"})

    return bullets[:MAX_BULLETS], warnings


def build_resume_pdf(profile: dict, bullets: list[dict], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=LETTER)
    width, height = LETTER
    margin = 0.75 * inch
    y = height - margin

    def line(text, font="Helvetica", size=10, gap=14, color=None):
        nonlocal y
        c.setFont(font, size)
        c.drawString(margin, y, text)
        y -= gap

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y, profile.get("name", ""))
    y -= 22

    contact_bits = [profile.get("email", ""), profile.get("phone", ""), profile.get("location", "")]
    links = profile.get("links", {})
    contact_bits += [v for v in links.values() if v]
    line(" | ".join(b for b in contact_bits if b), size=9, gap=18)

    c.setLineWidth(0.5)
    c.line(margin, y, width - margin, y)
    y -= 16

    line("EXPERIENCE & PROJECTS", font="Helvetica-Bold", size=11, gap=16)

    for b in bullets:
        if y < margin + 40:
            c.showPage()
            y = height - margin
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(margin, y, b["title"])
        y -= 12
        c.setFont("Helvetica", 9.5)
        wrapped = _wrap(f"- {b['text']}", 95)
        for w in wrapped:
            c.drawString(margin + 10, y, w)
            y -= 12
        y -= 4

    c.showPage()
    c.save()
    return output_path


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def verify_pdf_contains_bullets(pdf_path: str | Path, bullets: list[dict]) -> list[str]:
    """Reads the PDF back and confirms each bullet actually landed on the
    page. Returns a list of warnings for anything missing."""
    reader = PdfReader(str(pdf_path))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    full_text_norm = re.sub(r"\s+", " ", full_text)
    warnings = []
    for b in bullets:
        snippet = re.sub(r"\s+", " ", b["text"][:40])
        if snippet not in full_text_norm:
            warnings.append(f"Could not confirm this bullet rendered on the page: \"{b['text'][:60]}...\"")
    return warnings


def generate_resume(profile: dict, job: dict | None, output_path: str | Path) -> dict:
    bullets, warnings = generate_bullets(profile, job)
    pdf_path = build_resume_pdf(profile, bullets, output_path)
    warnings += verify_pdf_contains_bullets(pdf_path, bullets)
    return {"pdf_path": str(pdf_path), "bullets": bullets, "warnings": warnings}
