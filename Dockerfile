FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN cp .env.example .env

ENV HERMES_WEBUI_HOST=0.0.0.0

EXPOSE 8787

# server.py reads HOST/PORT only from env vars (HERMES_WEBUI_HOST / HERMES_WEBUI_PORT),
# NOT from CLI args. Railway injects $PORT, so honor it.
CMD ["sh", "-c", "HERMES_WEBUI_PORT=${PORT:-8787} python3 server.py"]
