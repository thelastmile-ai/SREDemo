---
feature: Dynamic Incident Input
solution: SREDemo Hackathon
status: planned
---

# Feature: Dynamic Incident Input

## Purpose
Allow the operator to type any incident description into a text box instead of auto-playing a fixed VPN scenario. The mock runner picks the closest pre-scripted story (VPN flap, DB pool exhaustion, K8s crashloop, SSL cert expiry) by keyword matching so any plausible variation still yields a compelling live demo.

## User Story
> As a hackathon judge evaluating this demo, I want to type an incident description in my own words so I can see the agent respond to my specific scenario rather than a canned walkthrough.

## Acceptance Criteria

- [ ] The dashboard shows an `IncidentInput` text area and **Send** button before any run starts
- [ ] The **Send** button is disabled until at least 10 characters have been typed
- [ ] Submitting the form calls `POST /api/start` with the typed `message` in the body
- [ ] The mock runner maps the message to one of four pre-scripted scenarios via keyword matching:
  - Keywords `vpn`, `tunnel`, `bgp`, `ipsec` → VPN tunnel flap script
  - Keywords `db`, `database`, `connection pool`, `postgres`, `sql` → DB pool exhaustion script
  - Keywords `k8s`, `pod`, `crashloop`, `kubernetes`, `oom` → K8s crashloop script
  - Keywords `ssl`, `cert`, `tls`, `expir` → SSL cert expiry script
  - No keyword match → VPN flap (safe default)
- [ ] The `IncidentPanel` component shows the operator's typed message (not the hardcoded scenario blurb)
- [ ] The rest of the demo flow (HITL, execution, report) is unchanged

## API Changes

### `POST /api/start` (updated)
```json
// request — message is now required
{ "session_id": "uuid", "message": "VPN tunnels are flapping on the Boston office link" }

// response — unchanged
{ "started": true }
```

## Mock Incident Scripts

Each script is a self-contained Python dict / function that matches the existing `_MOCK_PLAN_STEPS` / `_MOCK_STEP_OUTPUTS` / `_MOCK_REPORT` pattern.

| Script key | Scenario | Steps | Users impacted |
|-----------|----------|-------|----------------|
| `vpn_flap` | VPN tunnel flap — Boston/NY/Chicago | 11 | 450 |
| `db_pool` | PostgreSQL connection pool exhausted — checkout service | 8 | 200 |
| `k8s_crash` | K8s payment-service pods crashlooping (OOMKilled) | 9 | 80 |
| `ssl_expiry` | SSL cert expired on api.acme.com | 6 | 1200 |

## Example Prompt Guidance

The `IncidentInput` component shows four clickable example chips below the textarea — one per script. Clicking a chip fills the textarea with a realistic sample phrase so demo operators know exactly what to type and judges can drive the demo themselves.

| Chip label | Sample phrase inserted |
|-----------|------------------------|
| 🔌 VPN Flap | `VPN tunnels are flapping between Boston and Chicago — BGP sessions dropping intermittently` |
| 🐘 DB Overload | `PostgreSQL connection pool exhausted on checkout-service — getting "too many connections" errors` |
| ☸ K8s Crashloop | `payment-service pods are crashlooping in production — OOMKilled, restarting every 30 seconds` |
| 🔒 SSL Expiry | `SSL certificate expired on api.acme.com — users getting browser security warnings` |

Chips are displayed as pill badges with an icon and short label. When a chip is clicked the textarea receives focus with the full sample text; the operator can edit before hitting Send.

Placeholder text in the textarea also reads:
> "Describe an incident… e.g. 'VPN tunnels flapping on Boston link'"

## Out of Scope
- Natural-language scenario generation (mock scripts are sufficient for hackathon)
- Saving the typed message to the plan history store (covered in Section 3)
