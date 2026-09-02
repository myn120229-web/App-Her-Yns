"""
Younes Nazarian — Learning System
FastAPI backend · serves portfolio, contact API
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone
from pathlib import Path
import json, os, uuid, logging

BASE_DIR = Path(__file__).parent
PUBLIC_DIR = BASE_DIR / "public"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
MESSAGES_FILE = DATA_DIR / "messages.json"
VISITS_FILE = DATA_DIR / "visits.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger("learning-system")

app = FastAPI(title="Younes Nazarian — Learning System", version="2.0.0", docs_url="/api/docs", redoc_url=None)

class ContactMessage(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    message: str = Field(..., min_length=10, max_length=5000)
    company: str | None = Field(default=None, max_length=0)

def _read(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except: return default
def _write(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
def _visit():
    d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    v = _read(VISITS_FILE, {})
    v[d] = v.get(d, 0) + 1
    _write(VISITS_FILE, v)

@app.get("/api/health")
async def health(): return {"status":"ok","system":"learning-system","time":datetime.now(timezone.utc).isoformat()}

@app.get("/api/projects")
async def projects():
    return {"projects":[
        {"id":"01","label":"Classification","name":"Customer Churn Predictor","domain":"SaaS · Telecom","problem":"Which subscribers will leave before they do.","approach":"Classification pipeline with churn-cohort analysis and cohort dashboard.","signal":"Tenure & contract type surface as dominant features after EDA.","result":"Evaluation metric in case study — recall optimized for retention action.","stack":["Python","Pandas","Scikit-learn","Seaborn","Streamlit"]},
        {"id":"02","label":"Temporal","name":"Sales Forecasting Engine","domain":"E-Commerce · Retail · Rossmann","problem":"What will 1,115 stores sell tomorrow.","approach":"Temporal modeling with promo, calendar & rolling-mean features.","signal":"Seasonal structure plus promo lifts drive the forecast signal.","result":"Evaluation metric in case study — temporal cross-validation.","stack":["Python","Time Series","Feature Eng.","Scikit-learn"]},
        {"id":"03","label":"Probability","name":"Credit Risk Scorer","domain":"Fintech · Banking","problem":"Who will default, and why does the system think so.","approach":"Imbalanced-classification pipeline with per-decision explanations for compliance.","signal":"Probability distribution with a deliberate threshold.","result":"Evaluation metric in case study — precision tuned for regulatory use.","stack":["Sklearn Pipeline","SMOTE","PR Analysis","Explainability"]},
    ]}

@app.post("/api/contact")
async def contact(msg: ContactMessage, request: Request):
    if msg.company: raise HTTPException(400, "Spam")
    entry = {"id":str(uuid.uuid4())[:8],"name":msg.name.strip(),"email":msg.email,"message":msg.message.strip(),"ip":request.client.host if request.client else "unknown","received_at":datetime.now(timezone.utc).isoformat()}
    msgs = _read(MESSAGES_FILE, [])
    msgs.append(entry); _write(MESSAGES_FILE, msgs)
    log.info(f"contact {entry['id']} from {entry['name']}")
    return {"ok":True,"id":entry["id"],"received_at":entry["received_at"]}

@app.get("/api/stats")
async def stats():
    msgs=_read(MESSAGES_FILE,[]); visits=_read(VISITS_FILE,{})
    return {"messages":len(msgs),"visits":sum(visits.values()),"by_day":visits}

@app.get("/", include_in_schema=False)
async def index():
    _visit()
    return FileResponse(PUBLIC_DIR/"index.html")

app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")

if __name__=="__main__":
    import uvicorn; uvicorn.run("server:app",host="0.0.0.0",port=int(os.environ.get("PORT",8000)))
