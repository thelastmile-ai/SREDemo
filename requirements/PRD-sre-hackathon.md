# PRD: SREDemo Hackathon Enhancement — Plan Memory & Live Interaction

## Overview

Elevate SREDemo from a pre-scripted slide-deck replacement into a live, interactive AI platform demo worthy of winning a hackathon. The enhancements make the agent feel genuinely intelligent: it accepts any typed incident, asks clarifying questions when the request is ambiguous, shows its historical memory of past incidents, and makes the context budget lifecycle dramatically visible.

## Business Requirements

- [ ] Users type any incident description — the agent adapts its plan to the specific input rather than replaying a fixed script
- [ ] When the agent encounters ambiguity it pauses and asks the operator a clarifying question before planning; the operator's answer shapes the resulting plan
- [ ] A "Plan History" panel shows previously resolved incidents (pre-seeded + session completions); any user can see what the agent has learned and reuse past playbooks
- [ ] The context budget lifecycle (growth → warning → compaction → recovery) is visually unmissable — judges see it without being told to look
- [ ] The full demo runs with `USE_MOCK_LLM=true` and no cloud credentials

## Non-Functional Requirements

- All four enhancements integrate with the existing dark-theme React dashboard — no layout restructuring
- Each enhancement is independently deployable — shipping Section 1 alone produces a working demo
- Mock runner supports at least four incident scripts (VPN flap, DB connection pool exhaustion, K8s crashloop, SSL cert expiry) dispatched by keyword matching
- Compaction animation must be visible on a projector at 1920×1080 in a bright room

## Out of Scope

- Connecting plan history to a live PostgreSQL database (DB-backed persistence is an AgentCore concern; SREDemo uses an in-memory store for hackathon)
- Real LLM calls for the clarification round (mock scripted Q&A is sufficient)
- Mobile / tablet layouts

---

## Solutions

### Solution 1: Dynamic Incident Input
Replace hardcoded VPN scenario with a free-text incident input box. Mock runner dispatches to the nearest pre-scripted scenario by keyword matching.
- Status: **planned**
- Feature: `requirements/features/sre-hackathon-incident-input.md`
- Design: `design/hackathon/section-1-incident-input/`

### Solution 2: Clarification HITL Round
Add a mid-stream ambiguity gate: after intent extraction the mock runner can pause and ask the operator a clarifying question before generating the plan.
- Status: **planned**
- Feature: `requirements/features/sre-hackathon-clarification-hitl.md`
- Design: `design/hackathon/section-2-clarification-hitl/`

### Solution 3: Plan History Panel
In-memory history store populated from completed runs (pre-seeded with realistic entries). Displayed as a scrollable panel alongside the dashboard.
- Status: **planned**
- Feature: `requirements/features/sre-hackathon-plan-history.md`
- Design: `design/hackathon/section-3-plan-history/`

### Solution 4: Budget Visibility & Compaction Drama
Three-zone colour budget bar, sticky threshold warning banner, and a full-width compaction animation strip that fires when the sliding-window eviction triggers.
- Status: **planned**
- Feature: `requirements/features/sre-hackathon-budget-drama.md`
- Design: `design/hackathon/section-4-budget-drama/`
