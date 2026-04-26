---
feature: HTTP Client — AgentClient for AgentGateway
solution: SREDemo UI
status: planned
---

# Feature: HTTP Client

## Purpose
Provide an `AgentClient` that calls AgentGateway over HTTP instead of running AgentCore in-process. This enables the full platform stack (AuthService → AgentGateway → AgentCore) to be exercised from SREDemo when `USE_SYNTHETIC_DATA=false` and both services are running.

## Inputs
- `AUTH_SERVICE_URL` env var — e.g. `http://auth-service:9000`
- `AGENT_API_URL` env var — e.g. `http://agent-gateway:8000`
- `AGENT_USERNAME` + `AGENT_PASSWORD` env vars (for login)
- `AGENT_LLM_MODEL` env var — optional model override
- Bearer JWT issued by AuthService

## Outputs
- `access_token: str` from `POST /auth/token`
- `list[dict]` of supported models from `GET /models`
- `InvokeResponse` dict (`thread_id`, `result`, `context_budget`) from `POST /invoke`
- `ResumeResponse` dict (`thread_id`, `result`, `context_budget`) from `POST /resume`

## Behaviour

### `login(username, password) -> str`
1. POST to `{AUTH_SERVICE_URL}/auth/token` with form-encoded `username` + `password`.
2. Extract `access_token` from response JSON.
3. Store token for subsequent calls.
4. Raise `httpx.HTTPStatusError` on failure (caller handles and shows error in UI).

### `get_models() -> list[dict]`
1. GET `{AGENT_API_URL}/models` — no auth required.
2. Return list of `{model_id, provider, context_limit, display_name}`.
3. Used by `app.py` to populate the model shown in the login success line.

### `invoke(message, llm_model) -> dict`
1. POST `{AGENT_API_URL}/invoke` with `{message, llm_model}` body and `Authorization: Bearer <token>` header.
2. Return full response dict including `context_budget` field.
3. `thread_id` stored by caller for subsequent resume calls.

### `resume(thread_id, response) -> dict`
1. POST `{AGENT_API_URL}/resume` with `{thread_id, response}` body and `Authorization: Bearer <token>` header.
2. Return full response dict including `context_budget` field.

> **Note:** In the current platform state, AgentGateway's `/invoke` and `/resume` routes stub the AgentCore graph call (returning `result: {}`). `AgentClient` is wired now so it is ready when AgentGateway completes graph integration. Until then, `USE_SYNTHETIC_DATA=true` (in-process mode) is the working demo path.

## File Structure
```
sre_demo/
  client.py    — AgentClient class
```

## Config / Env Vars

| Var | Default | Description |
|-----|---------|-------------|
| `AUTH_SERVICE_URL` | `http://auth-service:9000` | AuthService base URL |
| `AGENT_API_URL` | `http://agent-gateway:8000` | AgentGateway base URL |
| `AGENT_USERNAME` | — | Demo user username for `POST /auth/token` |
| `AGENT_PASSWORD` | — | Demo user password |
| `AGENT_LLM_MODEL` | — | Optional model override; falls back to first model from `GET /models` |

## Acceptance Criteria
- [ ] `login()` obtains a JWT and stores it for subsequent calls
- [ ] `get_models()` returns the model list without authentication
- [ ] `invoke()` and `resume()` send the correct `Authorization` header
- [ ] HTTP errors surface as exceptions; `app.py` catches and displays them via `ui.py`
- [ ] `client.py` has no dependency on AgentCore — pure httpx
- [ ] `.env.example` documents `AGENT_USERNAME`, `AGENT_PASSWORD`, `AGENT_LLM_MODEL`
- [ ] `docker-compose.yml` passes `AGENT_USERNAME` and `AGENT_PASSWORD` to the `sre-demo` service

## Future Considerations
- Token refresh: re-login automatically when a 401 is returned mid-session
- `context_budget` from HTTP responses wired directly into the budget display (replaces simulated compaction)
