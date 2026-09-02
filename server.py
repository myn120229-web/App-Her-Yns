"""
Younes Nazarian — Personal Website Backend
FastAPI + Uvicorn — serves portfolio, contact API, visitor analytics.

Endpoints:
  GET  /                  → portfolio (public/index.html)
  GET  /api/health        → health check
  POST /api/contact       → contact form (saves to data/messages.json + email log)
  GET  /api/stats         → visitor + message stats
  GET  /api/projects      → project data (JSON)
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone
from pathlib import Path
import json, os, uuid, logging

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #
BASE_DIR   = Path(__file__).parent
PUBLIC_DIR = BASE_DIR / "public"
DATA_DIR   = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
MESSAGES_FILE = DATA_DIR / "messages.json"
VISITS_FILE   = DATA_DIR / "visits.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("younes-site")

app = FastAPI(
    title="Younes Nazarian — Portfolio API",
    description="Backend for personal portfolio: contact form, analytics, project data.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

# ------------------------------------------------------------------ #
# Models
# ------------------------------------------------------------------ #
class ContactMessage(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    message: str = Field(..., min_length=10, max_length=5000)
    # simple honeypot for bots — real users never fill this
    company: str | None = Field(default=None, max_length=0)

class ContactResponse(BaseModel):
    ok: bool
    id: str
    received_at: str

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _track_visit():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    visits = _read_json(VISITS_FILE, {})
    visits[today] = visits.get(today, 0) + 1
    _write_json(VISITS_FILE, visits)

# ------------------------------------------------------------------ #
# API routes
# ------------------------------------------------------------------ #
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "younes-portfolio", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/projects")
async def projects():
    """Project data used by the frontend (single source of truth)."""
    return {
        "projects": [
            {
                "id": "churn-predictor",
                "domain": "SaaS / Telecom",
                "name": "Customer Churn Predictor",
                "description": "End-to-end classifier that flags at-risk subscribers before they leave, with a Streamlit business dashboard.",
                "stack": ["Python", "Pandas", "Scikit-learn", "Seaborn", "Streamlit"],
                "metrics": [
                    {"label": "Recall (churn)", "value": "84%"},
                    {"label": "At-risk MRR flagged", "value": "$180k"},
                ],
                "github": "https://github.com/myn120229-web",
                "snippet": "from sklearn.ensemble import RandomForestClassifier",
            },
            {
                "id": "sales-forecast",
                "domain": "E-Commerce / Retail",
                "name": "Sales Forecasting Engine — Rossmann",
                "description": "Time-series forecaster across 1,115 stores with promo and calendar features.",
                "stack": ["Python", "Time Series", "Feature Eng.", "Scikit-learn"],
                "metrics": [
                    {"label": "MAPE", "value": "<12%"},
                    {"label": "Est. stockout reduction", "value": "23%"},
                ],
                "github": "https://github.com/myn120229-web",
                "snippet": "import statsmodels.api as sm",
            },
            {
                "id": "credit-risk",
                "domain": "Fintech / Banking",
                "name": "Credit Risk Scorer + Explainability",
                "description": "Imbalanced-classification pipeline with per-decision explanations for regulatory compliance.",
                "stack": ["Sklearn Pipeline", "SMOTE", "PR Analysis", "SHAP"],
                "metrics": [
                    {"label": "Precision (default)", "value": "78%"},
                    {"label": "Explainability", "value": "Audit-ready"},
                ],
                "github": "https://github.com/myn120229-web",
                "snippet": "from imblearn.over_sampling import SMOTE",
            },
        ]
    }

@app.post("/api/contact", response_model=ContactResponse)
async def contact(msg: ContactMessage, request: Request):
    """Receive contact-form submissions, persist to JSON log."""
    if msg.company:  # honeypot filled → bot
        raise HTTPException(status_code=400, detail="Spam detected")

    entry = {
        "id": str(uuid.uuid4())[:8],
        "name": msg.name.strip(),
        "email": msg.email,
        "message": msg.message.strip(),
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown")[:200],
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    messages = _read_json(MESSAGES_FILE, [])
    messages.append(entry)
    _write_json(MESSAGES_FILE, messages)

    log.info(f"New contact message from {entry['name']} <{entry['email']}> (id={entry['id']})")
    return ContactResponse(ok=True, id=entry["id"], received_at=entry["received_at"])

@app.get("/api/stats")
async def stats():
    messages = _read_json(MESSAGES_FILE, [])
    visits = _read_json(VISITS_FILE, {})
    return {
        "total_messages": len(messages),
        "total_visits": sum(visits.values()),
        "visits_by_day": visits,
        "last_message": messages[-1]["received_at"] if messages else None,
    }

# ------------------------------------------------------------------ #
# Static frontend (mounted LAST so /api/* takes priority)
# ------------------------------------------------------------------ #
@app.get("/", include_in_schema=False)
async def index():
    _track_visit()
    return FileResponse(PUBLIC_DIR / "index.html")

app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")

# ------------------------------------------------------------------ #
# Entry
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
