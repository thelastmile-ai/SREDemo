# Build context: AgenticFrmk/ (one level above SREDemo)
# docker-compose passes context: ../  and dockerfile: SREDemo/Dockerfile

# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build

COPY SREDemo/sre_demo/web/frontend/package.json SREDemo/sre_demo/web/frontend/package-lock.json* ./
RUN npm ci --prefer-offline 2>/dev/null || npm install

COPY SREDemo/sre_demo/web/frontend/ .
RUN npm run build

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.13-alpine

RUN apk add --no-cache git

WORKDIR /app

# Install AgentCore from local source — no GitHub token required
COPY AgentCore/ /agentcore/
RUN pip install --no-cache-dir /agentcore/

# Install SREDemo dependencies (agentcore excluded — installed above)
COPY SREDemo/pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy SREDemo application source
COPY SREDemo/ .

# Copy compiled React assets into the location server.py expects
COPY --from=frontend-builder /build/dist /app/sre_demo/web/frontend/dist

EXPOSE 3000

CMD ["python", "-m", "sre_demo.web.server"]
