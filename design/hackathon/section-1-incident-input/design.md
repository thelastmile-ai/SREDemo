# Design: Section 1 — Dynamic Incident Input

## HLD

### Component Diagram

```mermaid
graph LR
    subgraph Browser
        IP[IncidentInput<br/>component]
        EC[ExampleChips<br/>4 clickable pills]
        DP[DashboardPage]
        IF[IncidentPanel<br/>updated]
    end

    subgraph FastAPI server.py
        START[POST /api/start<br/>+ message field]
        DISPATCH[_dispatch_script<br/>keyword matcher]
        VPN[vpn_flap script]
        DB[db_pool script]
        K8S[k8s_crash script]
        SSL[ssl_expiry script]
    end

    EC -->|chip click fills textarea| IP
    IP -->|POST /api/start {message}| START
    START --> DISPATCH
    DISPATCH -->|vpn/tunnel/bgp| VPN
    DISPATCH -->|db/postgres/pool| DB
    DISPATCH -->|k8s/pod/crash| K8S
    DISPATCH -->|ssl/cert/tls| SSL
    VPN & DB & K8S & SSL -->|_MOCK_PLAN_STEPS etc.| START
    DP -->|renders typed message| IF
```

### Data Flow
1. Dashboard renders `IncidentInput` (placeholder textarea + Send) and `ExampleChips` (4 pill badges) before any run is started.
2. Operator types incident → clicks Send → `POST /api/start { session_id, message }`.
3. Server stores `message` on the `DemoSession`; calls `_dispatch_script(message)` → returns one of four script bundles (`steps`, `outputs`, `report`, `needs_clarification`).
4. The mock runner uses that bundle exactly as the hardcoded statics worked before.
5. `IncidentPanel` receives the typed message via session state and renders it.

### Key Decisions
- **Keyword dispatch over ML**: A simple `if/elif` on lowercased keywords is deterministic and never fails during a demo — no API call, no latency, no hallucination.
- **Script bundle pattern**: Each script is a `ScriptBundle` dataclass (steps, outputs, report text, `needs_clarification` flag). The mock runner is parameterised on a bundle — no code duplication.
- **`/api/start` backward-compatible**: `message` is required (no default). Old callers that don't send it get a 422 validation error — acceptable since SREDemo owns the only caller.

---

## LLD

### Python — `server.py`

```python
@dataclass
class ScriptBundle:
    steps: list[dict]
    step_outputs: dict[str, Any]
    report: str
    entities: dict
    needs_clarification: bool
    clarification_question: str

_SCRIPTS: dict[str, ScriptBundle] = {
    "vpn_flap":   ScriptBundle(...),
    "db_pool":    ScriptBundle(...),
    "k8s_crash":  ScriptBundle(...),
    "ssl_expiry": ScriptBundle(...),
}

_KEYWORD_MAP: list[tuple[list[str], str]] = [
    (["vpn", "tunnel", "bgp", "ipsec", "ike"], "vpn_flap"),
    (["db", "database", "connection pool", "postgres", "sql", "pg"], "db_pool"),
    (["k8s", "kubernetes", "pod", "crashloop", "oom", "evicted"], "k8s_crash"),
    (["ssl", "cert", "tls", "expir", "https", "certificate"], "ssl_expiry"),
]

def _dispatch_script(message: str) -> ScriptBundle:
    lower = message.lower()
    for keywords, key in _KEYWORD_MAP:
        if any(kw in lower for kw in keywords):
            return _SCRIPTS[key]
    return _SCRIPTS["vpn_flap"]   # safe default
```

### `StartRequest` model (updated)
```python
class StartRequest(BaseModel):
    session_id: str
    message: str   # was missing; now required
```

### `DemoSession` (updated)
```python
@dataclass
class DemoSession:
    ...
    message: str = ""          # operator's typed incident
    script: ScriptBundle | None = None   # resolved on /api/start
```

### `_run_demo_mock` signature change
```python
async def _run_demo_mock(session: DemoSession) -> None:
    bundle = session.script   # instead of module-level _MOCK_PLAN_STEPS
    ...
```

### React — `IncidentInput.tsx`
```tsx
interface IncidentInputProps {
  sessionId: string
  onStarted: (message: string) => void
}
// Renders:
//   <ExampleChips onSelect={setText} />
//   <textarea
//     placeholder='Describe an incident… e.g. "VPN tunnels flapping on Boston link"'
//     value={text}
//     onChange={...}
//   />
//   <button disabled={text.trim().length < 10}>Send ↵</button>
// On submit: calls api.start(sessionId, message), then onStarted(message)
```

### React — `ExampleChips.tsx` (new)
```tsx
const EXAMPLES = [
  {
    label: "🔌 VPN Flap",
    text: "VPN tunnels are flapping between Boston and Chicago — BGP sessions dropping intermittently",
  },
  {
    label: "🐘 DB Overload",
    text: "PostgreSQL connection pool exhausted on checkout-service — getting 'too many connections' errors",
  },
  {
    label: "☸ K8s Crashloop",
    text: "payment-service pods are crashlooping in production — OOMKilled, restarting every 30 seconds",
  },
  {
    label: "🔒 SSL Expiry",
    text: "SSL certificate expired on api.acme.com — users getting browser security warnings",
  },
]

interface ExampleChipsProps {
  onSelect: (text: string) => void
}

// Renders a row of pill <button> elements, one per EXAMPLES entry.
// Clicking calls onSelect(entry.text) which fills the parent textarea.
// Visual: rounded-full, border border-[#1c2333], hover:border-purple-500/50,
//         text-[#8b949e] hover:text-white, text-xs, gap-2 flex-wrap
// Label: "Try an example:" prefix in muted text, then the chips
```

### `api.ts` change
```ts
start(sessionId: string, message: string): Promise<void>
// POST /api/start { session_id, message }
```

### `DashboardPage` state machine change
```
idle → typing (IncidentInput visible)
typing → running (on start success, IncidentInput unmounts, stream connects)
```

### DB Schema Changes
None — in-memory only.

### Error Handling

| Scenario | Behaviour |
|----------|-----------|
| `message` missing from request | FastAPI returns 422 Unprocessable Entity |
| No keyword matches | Silently falls back to `vpn_flap` script |
| Start called twice on same session | Existing 409 Conflict unchanged |

### Config / Env Vars
None new.

---

## Sequence Diagrams

### Happy Path — Operator Uses Example Chip

```mermaid
sequenceDiagram
    actor Operator
    participant UI as React (DashboardPage)
    participant Server as FastAPI (server.py)

    UI->>Operator: shows IncidentInput + ExampleChips ("Try an example: 🔌 VPN Flap …")
    Operator->>UI: clicks "🔌 VPN Flap" chip
    UI->>UI: textarea fills with "VPN tunnels are flapping between Boston and Chicago…"
    Note over UI: operator may edit text before sending
    Operator->>UI: clicks Send
    UI->>Server: POST /api/start {session_id, message}
    Server->>Server: _dispatch_script("vpn tunnels…") → vpn_flap bundle
    Server->>Server: session.script = vpn_flap; create_task(_run_demo_mock)
    Server-->>UI: {started: true}
    UI->>Server: GET /api/stream?session_id=…
    UI->>UI: IncidentInput unmounts, stream begins
    Server-->>UI: node_start {node: "extract_intent"}
    Note over UI: normal demo flow continues
```

### Error Path — No Keyword Match

```mermaid
sequenceDiagram
    actor Operator
    participant UI as React
    participant Server as FastAPI

    Operator->>UI: types "something went wrong with the network"
    UI->>Server: POST /api/start {session_id, message}
    Server->>Server: _dispatch_script → no match → vpn_flap (default)
    Server-->>UI: {started: true}
    Note over Server: vpn_flap script plays; operator sees VPN scenario
```
