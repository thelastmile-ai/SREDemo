# Luma Submission — Agentic Seattle Hackathon

## Project Name
**AgenticFrmk — Production-Grade Agentic Infrastructure**

## Tagline
One sentence. The AI investigates, plans, and remediates your production incident. You approve.

---

## Short Description (paste into Luma form)

> **AgenticFrmk** is a production-grade agentic platform that turns natural language into a human-reviewed, auditable, parallel remediation plan — and executes it reliably.
>
> **SREDemo** shows it in action: an SRE types one plain-English sentence about a P1 incident. The agent classifies intent, extracts entities, builds a dependency-aware execution plan, presents it for human approval, and runs it step-by-step — live streaming every result to the UI.
>
> What separates this from every other agent demo: an **AgentGateway** that handles JWT auth, session binding, and real-time context budget management (sliding window compaction + summarisation on eviction). A **Plan History panel** where past incident resolutions become few-shot examples for future incidents. And a **live context budget gauge** that makes the AI's memory consumption visible and trustworthy — because enterprise teams won't trust a black box.
>
> This isn't a proof-of-concept. It ships with 121 passing tests, Alembic migrations, a Docker Compose stack, and a full React web UI. It's the framework you'd actually deploy.

---

## What It Does (bullet form — for Luma fields that ask this separately)

- SRE types one plain-English incident description — no alert IDs, no forms
- Agent asks one targeted clarification question if the incident is ambiguous
- Builds a grounded, dependency-aware step DAG — no hallucinated tool names
- Presents the full plan for human approval before a single change is made
- Executes steps in parallel (dependency order), streaming each result live
- Delivers root cause, actions taken, and follow-up recommendations
- Stores every resolution in Plan History — future similar incidents get few-shot acceleration
- Live context budget gauge + compaction banners make AI memory management visible

---

## How We Built It

**Stack:** AgentCore (LangGraph StateGraph) · AgentGateway (FastAPI + RS256 JWT + context management) · AuthService (RSA key pair JWT issuance) · Claude Sonnet 4.6 (orchestration) · React 18 + Vite + TypeScript (UI) · FastAPI + SSE (backend) · Docker multi-stage

**The novel parts:**
1. **AgentGateway** — a standalone service that enforces JWT auth, binds sessions to users, tracks token budget per session, applies sliding-window compaction, and summarises evicted context with entity fidelity checks
2. **Plan History + Few-Shot Learning** — past resolutions are stored and injected as few-shot examples when similar incidents recur; the UI shows a "Few-shot used" badge
3. **Context Budget Visibility** — a live arc gauge + sparkline + warning/compaction banners surface the AI's internal memory state to the user in real time

---

## Demo Video
`SREDemo-UI-Demo-Long.mp4` — full walkthrough including clarification gate, HITL approval, live execution, budget gauge animation, and plan history few-shot badge

---

## GitHub
https://github.com/AgenticFrmk/SREDemo

---

## Team
founders — Jaya, Raj full-stack, systems, and ML engineering
