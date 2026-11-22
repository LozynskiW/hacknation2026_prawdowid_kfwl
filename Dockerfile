# Jeden obraz dla backendu (strona WWW + API + agent OpenCode) i bota Discorda.
# Uruchomienie obu: docker compose up --build   (opis w README, sekcja "Docker")

# --- OpenCode V2: pakiet npm instaluje samodzielny plik wykonywalny dla tej platformy ---
FROM node:22-bookworm-slim AS opencode
ARG OPENCODE_VERSION=2.3.2
RUN npm install -g @opencode/cli@${OPENCODE_VERSION} \
 && cp /usr/local/lib/node_modules/@opencode/cli/bin/opencode.exe /opencode2 \
 && /opencode2 --version

# --- Aplikacja ---
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY --from=opencode /opencode2 /usr/local/bin/opencode2

WORKDIR /app
# Najpierw zależności (warstwa z cache), potem kod.
COPY pyproject.toml requirements.txt README.md ./
COPY src ./src
RUN pip install -r requirements.txt
# Konfiguracja agenta: OpenCode czyta ją z katalogu, w którym działa backend (/app).
COPY .opencode ./.opencode

# Bez roota. Dane (log sprawdzeń, stan OpenCode) w /app/data - wolumen w docker-compose.yml.
RUN useradd --create-home --uid 10001 prawdowid && mkdir -p /app/data && chown -R prawdowid /app/data
USER prawdowid

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

CMD ["uvicorn", "prawdowid.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
