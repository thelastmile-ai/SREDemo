---
feature: Plan History Panel
solution: SREDemo Hackathon
status: planned
---

# Feature: Plan History Panel

## Purpose
Show judges and other users that the agent has persistent memory of past incidents. A scrollable panel displays previously resolved incidents — pre-seeded with realistic historical entries and updated live as new runs complete. This demonstrates the plan-memory capability of AgentCore without requiring a database.

## User Story
> As a hackathon judge, I want to see that the agent has already resolved similar incidents before and can surface those learnings, proving it gets smarter over time.

## Acceptance Criteria

- [ ] A `PlanHistoryPanel` component is visible on the dashboard (collapsible sidebar or bottom strip, always present)
- [ ] The panel is pre-populated with at least 4 historical incidents on server startup (seeded in-memory)
- [ ] When a run completes (`report` SSE event received), the React app fetches `GET /api/history` and re-renders the panel with the new entry at the top
- [ ] Each history card shows: incident type badge, domain, one-line description, steps count, outcome badge (COMPLETED/FAILED), and time-ago string
- [ ] The panel has a "Used by agent" marker on the entry matching the current run's domain (showing the few-shot retrieval concept)
- [ ] `GET /api/history` returns the last 20 entries, newest first

## History Card Data Shape

```ts
interface HistoryEntry {
  id: string
  action: string          // "resolve_vpn_flap"
  domain: string          // "networking"
  description: string     // "VPN tunnel flap — Boston/NY/Chicago"
  outcome: "COMPLETED" | "FAILED"
  steps_count: number
  resolved_at: string     // ISO timestamp
  duration_seconds: number
}
```

## API Changes

### New: `GET /api/history`
```json
// response — array, newest first, max 20
[
  {
    "id": "hist-001",
    "action": "resolve_vpn_flap",
    "domain": "networking",
    "description": "VPN tunnel flap — Boston/NY/Chicago",
    "outcome": "COMPLETED",
    "steps_count": 11,
    "resolved_at": "2026-04-25T14:32:00Z",
    "duration_seconds": 342
  }
]
```

## Pre-Seeded Historical Data (4 entries)

| id | action | domain | description | outcome | steps |
|----|--------|--------|-------------|---------|-------|
| hist-001 | resolve_vpn_flap | networking | VPN tunnel flap — Boston/NY/Chicago (IKE phase 2 mismatch) | COMPLETED | 11 |
| hist-002 | resolve_db_pool_exhaustion | database | PostgreSQL connection pool exhausted — checkout service | COMPLETED | 8 |
| hist-003 | resolve_k8s_crashloop | kubernetes | payment-service pods OOMKilled in prod namespace | COMPLETED | 9 |
| hist-004 | resolve_ssl_expiry | security | SSL cert expired on api.acme.com — 1200 users blocked | FAILED | 4 |

## Panel UX

- Collapsible by default on narrow screens, expanded on wide screens (≥1440px)
- "Few-shot: used" badge on the entry whose `domain` matches the current run — fades in when the plan node completes
- Failed entries shown in muted red; completed in green
- Clicking a card expands it inline to show the steps list (read-only)

## Out of Scope
- Connecting to PostgreSQL plan_history table (AgentCore concern)
- Exporting history as JSON or CSV
