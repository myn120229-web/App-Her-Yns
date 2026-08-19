# Hermes WebUI (Deployed on Railway)

This repo hosts the [Hermes WebUI](https://github.com/nesquena/hermes-webui) deployed to Railway.

## Access
Once deployed, Railway provides a public URL. Open it in your browser or use it as a Telegram Mini App.

## Local dev
```
pip install -r requirements.txt
cp .env.example .env
python3 server.py --host 127.0.0.1 --port 8787
```

## Deploy
Railway auto-deploys from this repo's `main` branch using the Dockerfile.
