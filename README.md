# Younes Nazarian — The Learning System

Personal portfolio as an interactive system: CHAOS → STRUCTURE → SIGNAL → CONFIDENCE.

## Run

```bash
pip install -r requirements.txt
python server.py
# → http://localhost:8000
```

## Structure

```
├── server.py          # FastAPI — contact API, stats, static serving
├── requirements.txt
├── data/              # messages.json, visits.json (auto-managed)
└── public/
    ├── index.html     # Single-page experience
    ├── css/style.css  # Design system
    └── js/app.js      # Learning Field, toolchain, projects, form
```

## API

- `GET /api/health` — health
- `GET /api/projects` — project data
- `POST /api/contact` — contact form (honeypot-protected)
- `GET /api/stats` — visits/messages
