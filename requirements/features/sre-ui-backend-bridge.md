---
feature: FastAPI Backend Bridge — SSE streaming + REST API
solution: SREDemo UI
status: planned
---

# Feature: FastAPI Backend Bridge

## Purpose
A lightweight FastAPI server that runs AgentCore in-process (same as the current `demo.py` approach), exposes REST endpoints for the React frontend, and streams real-time agent events to the browser via Server-Sent Events (SSE). The backend also serves the compiled React static files so a single service handles both the API and the UI.

## Architecture

```
Browser (React)
    │  GET /                → serves index.html (React app)
    │  GET /assets/*        → serves React build artefacts
    │  POST /api/login      → returns session token
    │  GET  /api/stream     → SSE: real-time agent events
    │  POST /api/start      → starts the demo run
    │  POST /api/approve    → submits HITL response
    │
FastAPI (server.py)
    │  asyncio.Queue → SSE publisher
    │  AgentCore graph (in-process, MemorySaver)
    │  synthetic tool registry (patched at startup if USE_SYNTHETIC_DATA=true)
```

## Endpoints

### `POST /api/login`
Authenticate the demo user (simulated or real AuthService).

**Request body:**
```json
{ "username": "string", "password": "string" }
```
**Response:**
```json
{ "session_id": "uuid", "username": "string", "model": "claude-sonnet-4-6" }
```
**Behaviour:**
- Synthetic mode: accepts any credentials, returns a UUID session.
- Real mode (`USE_SYNTHETIC_DATA=false`): proxies to `POST {AUTH_SERVICE_URL}/auth/token`; returns JWT inside `session_id`.

---

### `GET /api/stream`
Server-Sent Events stream for the active demo session.

**Query param:** `session_id=<uuid>`

**Event types emitted:**

| Event type | Payload | Trigger |
|-----------|---------|---------|
| `node_start` | `{ node: str }` | Each graph node begins |
| `node_done` | `{ node: str }` | Each graph node completes |
| `entities` | `{ entities: dict }` | After `extract_entities` |
| `plan_ready` | `{ steps: list }` | After `plan` — triggers HITL modal |
| `step_result` | `{ step_id: str, status: str, output: any }` | After each `execute_step` |
| `budget` | `{ budget_used: float, estimated_tokens: int, context_limit: int, compacted: bool, messages_evicted: int, strategy: str }` | After plan and after execution |
| `report` | `{ text: str, metrics: dict }` | After `report` node |
| `error` | `{ message: str }` | Any unhandled exception |

**Behaviour:**
- The SSE connection is kept open for the session lifetime.
- Events are pushed from a per-session `asyncio.Queue` that the graph stream writes to.
- The React `useAgentStream` hook consumes this stream and dispatches events to component state.

---

### `POST /api/start`
Kick off the AgentCore demo run for a session.

**Request body:**
```json
{ "session_id": "uuid" }
```
**Response:** `{ "started": true }`

**Behaviour:**
1. Looks up session by `session_id`.
2. Starts `asyncio.create_task(run_demo(session))` — non-blocking.
3. `run_demo` streams `AgentState` updates into the session's SSE queue.
4. When the plan is ready (`plan.status == "PENDING_REVIEW"`), emits `plan_ready` and pauses — waiting for a `POST /api/approve`.

---

### `POST /api/approve`
Submit the HITL response and resume graph execution.

**Request body:**
```json
{ "session_id": "uuid", "response": "approved" }
```
**Response:** `{ "resumed": true }`

**Behaviour:**
1. Stores `response` in the session object.
2. Sets an `asyncio.Event` that `run_demo` is awaiting.
3. `run_demo` resumes graph execution from the HITL interrupt.

---

### `GET /health`
Returns `{ "status": "ok" }` — no auth required (used by Docker Compose healthcheck).

---

### Static file serving
FastAPI mounts the compiled React build at `/`. The Vite build output (`dist/`) is copied into the container at `/app/web/frontend/dist`. `StaticFiles` serves it; the catch-all `GET /{path}` returns `index.html` for React Router.

## Session Model

```python
@dataclass
class DemoSession:
    session_id: str
    username: str
    queue: asyncio.Queue          # SSE publisher
    hitl_event: asyncio.Event     # signals HITL response received
    hitl_response: str | None     # set by POST /api/approve
    task: asyncio.Task | None     # run_demo background task
```

Sessions stored in an in-memory dict — no persistence needed for demo.

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Unknown `session_id` | 404 |
| Graph exception in `run_demo` | Emit `error` SSE event; task marked done |
| SSE client disconnects | `asyncio.CancelledError` caught; session cleaned up |
| HITL approval before `plan_ready` | 409 Conflict |

## Config / Env Vars

| Var | Default | Description |
|-----|---------|-------------|
| `SERVER_PORT` | `3000` | Port the FastAPI server listens on |
| `USE_SYNTHETIC_DATA` | `true` | Patch tool registry with synthetic functions |
| `DEMO_CONTEXT_LIMIT` | `15000` | Token ceiling for budget display |
| `DEMO_COMPACT_THRESHOLD` | `0.80` | Fraction that triggers simulated compaction |

## File Structure

```
sre_demo/
  web/
    server.py           — FastAPI app: login, stream, start, approve, static files
    frontend/           — React + Vite project (see sre-ui-react-web.md)
```

## docker-compose.yml Changes

The `sre-demo` service:
- CMD changes to `python -m sre_demo.web.server`
- Port `3000:3000` exposed
- `ANTHROPIC_API_KEY` and `USE_SYNTHETIC_DATA` env vars passed through
- `depends_on: auth-service` (soft — only needed when `USE_SYNTHETIC_DATA=false`)

## Acceptance Criteria

- [ ] `GET /` returns the React app HTML
- [ ] `POST /api/login` returns a `session_id` for any credentials in synthetic mode
- [ ] `GET /api/stream` opens an SSE connection and keeps it alive
- [ ] `node_start` and `node_done` events arrive for each graph node
- [ ] `plan_ready` event is emitted when the plan is ready and graph is paused
- [ ] `POST /api/approve` resumes the graph; subsequent events arrive over SSE
- [ ] `step_result` events arrive for each executed step
- [ ] `budget` events arrive after the plan phase and after execution completes
- [ ] `report` event arrives when the graph completes
- [ ] `GET /health` returns `{ "status": "ok" }` with no auth
- [ ] The service starts with `docker compose up` on port `3000`

## Future Considerations
- Replay endpoint: serve pre-recorded event logs for offline demos
- Auth middleware: validate JWT from AuthService on API endpoints when real-stack mode is active
- Multiple concurrent sessions (currently single-session for simplicity)
