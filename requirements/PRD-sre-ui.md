# PRD: SREDemo UI — Agentic Web Application

## Overview

Transform SREDemo into a polished React web application suitable for VC demos and competition presentations. The application demonstrates the full AgentCore platform end-to-end — login, AI-driven SRE investigation, human-in-the-loop approval, remediation execution, and context budget management — through a visually compelling dark-themed dashboard. No cloud credentials required (synthetic data mode is the default).

## Business Requirements

- [ ] Users authenticate via a branded login page before the agent session starts
- [ ] The SRE troubleshooting workflow (intent → entities → plan → HITL → execute → report) is visualised as a live-updating dashboard with animated transitions
- [ ] HITL confirmation gate presents the remediation plan in a structured table and requires explicit approval or revision before execution proceeds
- [ ] The full demo runs with synthetic VPN tunnel flap data — no AWS, Datadog, or PagerDuty credentials required
- [ ] Token context usage is visualised with an animated gauge/bar; compaction and eviction events are highlighted with a visual animation
- [ ] The application is served over HTTP and accessible in a browser from `docker compose up`
- [ ] The UI is optimised for a widescreen presentation (16:9, 1920×1080 projector or 4K display)

## Non-Functional Requirements

- **Tech stack**: React 18 + Vite (frontend) · FastAPI (backend API bridge) · SSE (real-time agent streaming)
- **Design system**: Dark theme, terminal-inspired palette with neon accent colours; Tailwind CSS; Framer Motion for transitions
- **No external cloud calls at demo time** — synthetic mode is the default
- **Single `docker compose up`** starts the full stack; the React app is served on port `3000` by the backend
- **Responsive only down to 1280px** — demo-optimised, not mobile-first
- All agent streaming uses Server-Sent Events (SSE) — no WebSocket complexity

## Out of Scope

- Mobile / tablet layouts
- User session persistence across page reloads
- Multi-scenario selection at runtime
- Authentication with real AuthService in the default demo path

---

## Solutions

### Solution 1: React Web UI
Full React frontend: login page, live agent dashboard, HITL approval modal, execution feed, context budget gauge, and final report card.
- Status: **planned**
- Features: See `requirements/features/sre-ui-react-web.md`

### Solution 2: FastAPI Backend Bridge
FastAPI server that runs AgentCore in-process, streams events to the React frontend via SSE, and exposes REST endpoints for login, demo start, and HITL responses.
- Status: **planned**
- Features: See `requirements/features/sre-ui-backend-bridge.md`

### Solution 3: Synthetic Data Layer
Replace real AWS/Datadog/PagerDuty tool calls with pre-canned async functions returning realistic scenario data.
- Status: **planned**
- Features: See `requirements/features/sre-ui-synthetic-data.md`

### Solution 4: Context Budget Display
Animated token gauge with live counter, threshold warnings, and compaction animation — fed from the SSE stream.
- Status: **planned**
- Features: See `requirements/features/sre-ui-context-budget.md`

### Solution 5: HTTP Client
`AgentClient` for calling AgentGateway (`login`, `get_models`, `invoke`, `resume`) when running against the live stack.
- Status: **planned**
- Features: See `requirements/features/sre-ui-http-client.md`
