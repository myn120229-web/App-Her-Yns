# Younes Nazarian — Personal Portfolio

ML Engineer · Data Scientist · Python Developer

## Quick Start

```bash
pip install -r requirements.txt
python server.py
# → http://localhost:8000
```

## Project Structure

```
├── server.py            # FastAPI backend (contact API, analytics, static serving)
├── requirements.txt     # Python dependencies
├── data/                # Auto-created: messages.json, visits.json
└── public/              # Frontend
    ├── index.html       # Portfolio page
    ├── style.css        # Design system
    └── app.js           # Animations, panels, form handling
```

## Features

- **Glass morphism** design from LinkedIn banner DNA
- **3D layered panels** — fanning, parallax-responsive, animated
- **Contact form** — saves to `data/messages.json`, honeypot bot protection
- **Analytics** — daily visit counter at `/api/stats`
- **Project data** — single source of truth at `/api/projects`
- **Zero frameworks** — vanilla HTML/CSS/JS + FastAPI backend only

## Deploy

Any Python host (Railway, Render, Fly.io). Set `PORT` env var.

```bash
PORT=8000 python server.py
```

## License

Personal use only — © 2026 Younes Nazarian
