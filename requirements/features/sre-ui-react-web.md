---
feature: React Web UI — Login, Live Dashboard, HITL Gate, Report
solution: SREDemo UI
status: planned
---

# Feature: React Web UI

## Purpose
A polished, demo-ready React single-page application that makes the AgentCore platform immediately compelling to VCs and competition judges. Dark theme, animated transitions, real-time agent streaming, and a professional incident-management aesthetic. Every screen is designed to look impressive on a 1920×1080 projector.

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | React 18 + Vite | Fast HMR, modern JSX, small bundle |
| Styling | Tailwind CSS + custom CSS vars | Dark theme tokens, utility-first speed |
| Animation | Framer Motion | Smooth page transitions and micro-animations |
| Charts | Recharts | Token budget arc gauge and history sparkline |
| Icons | Lucide React | Consistent, clean icon set |
| Notifications | react-hot-toast | Non-blocking step completion toasts |
| Real-time | EventSource (SSE) | One-way server push; simpler than WebSocket |

## Screens

### 1. Login Page

**Layout:** Full-screen centred card on a dark gradient background.

**Elements:**
- Animated logo / wordmark: `AgentCore · SRE Demo` with a subtle pulse glow
- Tagline: `AI-powered incident remediation — powered by Claude + LangGraph`
- Username and password fields with animated focus states
- `Start Demo` button — primary CTA, gradient fill, scale animation on hover
- Below the fold: platform badge row (Anthropic, AWS, PagerDuty, Datadog icons)

**Behaviour:**
- On submit → POST `/api/login` → on success, navigate to the Dashboard
- Simulated mode: any username/password accepted instantly
- Error state: shake animation + red border on fields

---

### 2. Agent Dashboard (main screen)

Split layout — optimised for widescreen:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Header: logo · session ID · model badge · [context budget gauge]   │
├───────────────────────────┬─────────────────────────────────────────┤
│                           │                                         │
│   INCIDENT PANEL          │   AGENT ACTIVITY FEED                   │
│   (red alert card)        │   (scrolling live stream of node        │
│                           │    completions + reasoning)             │
│   ENTITY CARD             │                                         │
│   (extracted fields)      │                                         │
│                           │                                         │
├───────────────────────────┴─────────────────────────────────────────┤
│   PLAN / EXECUTION AREA (full width)                                │
└─────────────────────────────────────────────────────────────────────┘
```

**Header:**
- SREDemo logo (left)
- Session ID pill (centre)
- Model badge: `claude-sonnet-4-6` (right)
- Context budget arc gauge (top-right corner) — always visible

**Incident Panel:**
- Red glowing border card
- Severity badge: `P2` in bold red
- Incident title: `VPN Tunnel Flap — 3 Branch Offices`
- Incident description text
- Affected services row: `ERP`, `VoIP` chips
- Affected branches: `Boston`, `New York`, `Chicago` chips

**Agent Activity Feed:**
- Scrolling vertical timeline
- Each node appears as a new entry with animated slide-in:
  - Node name + icon
  - Status: `running...` (pulsing dot) → `✓ complete` (green)
  - Optional: short reasoning excerpt once complete

**Entity Card:**
- Appears after `extract_entities` completes
- Grid of extracted fields: domain, severity, incident type, affected branches, affected services, customer-facing
- Animated fade-in

**Plan / Execution Area:**
- Before HITL approval: shows the plan table (see HITL Gate below)
- During execution: shows the execution feed (see Execution Feed below)
- After report: shows the report card (see Report Card below)

---

### 3. HITL Approval Gate

Appears as an **overlay modal** over the dashboard when the plan is ready.

**Elements:**
- Modal title: `⚡ Human Approval Required`
- Subtitle: `Review the remediation plan before execution proceeds`
- Plan table:

  | Step | Tool | Dependencies | Status |
  |------|------|--------------|--------|
  | 1 | aws_describe_vpn_connections | — | PENDING |
  | ... | ... | ... | ... |

- Two CTAs:
  - `Approve & Execute` — green, primary, full-width
  - `Revise Plan` — secondary; expands a text area for feedback
- If `Revise Plan`: text area + `Submit Revision` button

**Behaviour:**
- Modal cannot be dismissed without an action (no backdrop click to close)
- On `Approve & Execute` → POST `/api/approve` → modal closes, Execution Feed begins
- On `Submit Revision` → POST `/api/revise` with feedback → modal closes, re-planning begins

---

### 4. Execution Feed

Replaces the Plan area after HITL approval.

**Layout:** Card with a scrolling list of step results.

**Per step entry:**
- Tool name + provider icon (AWS / Datadog / PagerDuty / Network)
- Status badge: `RUNNING` (animated spinner) → `✓ COMPLETED` (green) or `✗ FAILED` (red)
- Collapsed output preview (first 120 chars); expand arrow reveals full JSON
- Timestamp

**Toasts:**
- `react-hot-toast` success toast for each completed step
- Error toast (red) for any failure

---

### 5. Report Card

Replaces the Execution Feed area when the report is ready.

**Layout:** Full-width card with a green left border.

**Elements:**
- Title: `Incident Resolved ✓`
- Resolution time badge: `Resolved in 4m 32s`
- Three metric chips: `9 steps executed` · `3 tunnels reset` · `450 users restored`
- Root cause heading + body text from the agent report
- `Download Report` button (opens a print-friendly view)

---

## Routing

| Route | Screen |
|-------|--------|
| `/` | Login Page |
| `/demo` | Agent Dashboard (requires session) |

## Acceptance Criteria

- [ ] Login page renders on `/`; navigates to `/demo` on success
- [ ] Dashboard layout is correct at 1920×1080 — no overflow, no horizontal scroll
- [ ] Agent Activity Feed shows each node arriving via SSE with a slide-in animation
- [ ] Incident panel renders immediately on page load with P2 badge and branch chips
- [ ] Entity card fades in after `extract_entities` completes
- [ ] HITL modal blocks the UI — cannot proceed without an action
- [ ] HITL modal shows the full plan table
- [ ] `Approve & Execute` closes modal and starts execution feed
- [ ] `Revise Plan` expands text area and sends revision feedback
- [ ] Each executed step entry shows tool name, provider icon, status, and output preview
- [ ] Report card shows after all steps complete with resolution time and metrics
- [ ] Context budget gauge visible in header throughout the session
- [ ] All page transitions use Framer Motion animations
- [ ] App is served on port `3000` and accessible at `http://localhost:3000`

## File Structure

```
sre_demo/
  web/
    frontend/               — React + Vite project
      index.html
      vite.config.ts
      tailwind.config.ts
      src/
        main.tsx
        App.tsx             — router (Login / Dashboard)
        pages/
          LoginPage.tsx
          DashboardPage.tsx
        components/
          IncidentPanel.tsx
          ActivityFeed.tsx
          EntityCard.tsx
          PlanTable.tsx
          HitlModal.tsx
          ExecutionFeed.tsx
          ReportCard.tsx
          BudgetGauge.tsx   — arc gauge (Recharts)
          StepEntry.tsx
        hooks/
          useAgentStream.ts — SSE event consumer
          useSession.ts
        lib/
          api.ts            — fetch wrappers for /api/*
          types.ts          — shared TypeScript interfaces
    server.py               — FastAPI backend bridge (see sre-ui-backend-bridge.md)
```

## Future Considerations
- Replay mode: re-run the demo from a saved event log without calling the LLM
- Multi-scenario selector on the login page
- Dark/light theme toggle
- Shareable incident report link
