# AgenticFrmk — Investor Pitch

> *The production-grade agentic infrastructure layer that enterprises actually deploy.*

---

## The Problem

Every company is racing to deploy AI agents. Almost none of them work in production.

A P1 incident hits at 3 AM. The on-call SRE is paged. They spend **45–90 minutes** just on triage — grepping logs, cross-referencing Datadog, hunting for the right AWS connection ID. At **$5,600 per minute** in lost revenue (Gartner), that's a $250K–$500K event for a single incident.

The obvious answer is an AI agent. The problem is every agent framework built today is a demo:

| What demo agents do | What production needs |
|---------------------|----------------------|
| Single LLM call | Full stateful graph with 9 specialised nodes |
| Sequential steps | Automatic DAG-based parallel execution |
| Hope the agent gets it right | Two mandatory human approval gates |
| No crash recovery | Claim/lease with automatic re-claim on worker crash |
| Black-box reasoning | Explicit chain-of-thought trace surfaced to the user |
| One machine | Horizontal scale — Postgres / SQS / Pub/Sub swappable |
| No auth | JWT-verified, session-bound, user-identity-locked threads |
| No memory management | Real-time context budget tracking with sliding-window compaction |
| LLM guesses tool names and domain schemas | RegistryService grounds every LLM call in versioned, team-owned facts |

**These aren't edge cases. They're the default failure mode of every agent deployed today.**

---

## The Solution: AgenticFrmk

AgenticFrmk is a **production-grade agentic platform** consisting of five production services and a concrete enterprise use case demo:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           AgenticFrmk Platform                           │
│                                                                          │
│  AuthService    AgentGateway      AgentCore       RegistryService        │
│  ───────────    ───────────       ─────────       ───────────────        │
│  RS256 JWT  →   JWT verify   →    LangGraph   ←   Schema Registry        │
│  issuance       Session bind      StateGraph       (entity fields)       │
│  JWKS           Context budget    9 nodes          Tool Registry         │
│                 Compaction        HITL gates        (contracts+sigs)     │
│                 Model registry    DAG executor      Playbook Registry    │
│                                   121 tests         (ordering rules)     │
│                                                     Versioned · Audited  │
│                                                                          │
│                           SREDemo (use case)                             │
│                           ──────────────────                             │
│                           React web UI · FastAPI SSE                     │
│                           Plan History · Budget Gauge                    │
│                           4 incident scenarios                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### What Makes This a Platform, Not a Demo

**1. AgentGateway — the production entry point nobody else has built**

Every other framework skips straight from "prompt" to "LLM call." AgentGateway enforces the layer enterprises actually need:

- **RS256 JWT verification** via JWKS rotation — only authenticated users can invoke agents
- **Session identity binding** — only the originating user can resume a thread; no session hijacking
- **Real-time context budget management** — token counting per session, configurable thresholds
- **Sliding-window compaction** — when context fills, the gateway automatically evicts old messages, summarises them, and checks entity fidelity before proceeding
- **Model registry** (`GET /models`) — the UI knows exactly what models are available; no hardcoded strings

This is the difference between a demo and infrastructure that a Fortune 500 CISO will sign off on.

**2. Plan History + Few-Shot Learning — the agent that gets smarter**

Every incident resolution is stored. When a similar incident recurs, the agent pulls matching historical resolutions as few-shot examples. The UI shows a **"Few-shot used by agent"** badge on the relevant history card.

This creates a compounding moat: the longer a customer runs AgenticFrmk, the faster and more accurate the agent becomes on their specific infrastructure. Competitors starting fresh cannot replicate years of encoded institutional knowledge.

**3. Human-in-the-Loop as a Hard Gate — not a suggestion**

The executor cannot start without explicit human approval. Two interrupt gates:

| Gate | What the human sees | Options |
|------|---------------------|---------|
| Plan Review | Full step-by-step DAG with dependencies | Approve / Modify / Reject |
| CoT Confirm | Claude Opus's explicit reasoning trace walking the DAG | Confirm / Reject |

Modify routes back to the planner. The agent never acts on a plan the user hasn't approved. **The audit trail is the compliance artifact** — every change is human-approved and timestamped.

**4. RegistryService — the knowledge base that eliminates LLM hallucination**

Every other agent framework lets the LLM guess tool names, invent domain schemas, and produce step orderings that feel correct but violate domain constraints. RegistryService replaces guessing with registered facts:

| Registry | What it stores | LLM node that consumes it |
|----------|---------------|--------------------------|
| **Schema Registry** | Entity field definitions, valid domain names | `extract_intent` (valid domains), `extract_entities` (field schemas) |
| **Tool Registry** | Tool names, docstrings, input/output contracts | `plan` (real tool names + signatures — no hallucinated calls) |
| **Playbook Registry** | Domain ordering rules, hard constraints, soft hints | `plan` (e.g. *for K8s: always describe pods before patching; always notify PagerDuty before any change*) |

Domain teams register and update their own entries via REST API — no framework code changes, no redeploys. A new SRE domain goes live by calling `POST /schemas`, `POST /tools`, `POST /playbooks`. The LLM immediately reasons from the new facts.

Schema versions are compatibility-checked (BACKWARD / FORWARD / FULL / BREAKING) — the same model used by Confluent Schema Registry for Kafka, applied to LLM entity extraction. In-flight sessions pin the schema version they started with; breaking changes never corrupt active incident resolutions.

`ScalableRegistryClient` in AgentCore caches registry responses with a 60s TTL — no added latency on the hot path.

This is the multi-tenant enablement: different enterprise teams own their domains, evolve their schemas independently, and never touch each other's configuration.

**5. Context Budget Visibility — the trust layer**

Enterprise operators won't trust a black box. AgenticFrmk makes the AI's internal state visible:

- **Live arc gauge** shows real-time token consumption (green / amber / red)
- **Warning banner** slides in before the context limit — before degraded behaviour
- **Compaction banner** drops from the top of the screen when the gateway evicts context — the user sees exactly when the AI's memory is reset

This is the feature that enterprise SRE teams ask for. Nobody else ships it.

---

## SREDemo: The Business Case Made Concrete

### The Scenario

An SRE types one sentence:

> *"K8s pods are OOMKilled every 2 minutes in production — payment-service is down"*

No alert IDs. No runbook lookups. No Jira ticket. One sentence.

### What Happens in Under 5 Minutes

| Phase | Agent action | Time |
|-------|-------------|------|
| Intent | Classifies domain, action, severity from free text | ~3s |
| Clarify | Asks one targeted question (which namespace?) | ~5s |
| Entities | Extracts severity, service, namespace, error type | ~3s |
| Plan | Builds 7-step DAG — no hallucinated tool names | ~8s |
| **HITL** | **SRE reviews and approves the plan** | Human gate |
| Execute | Runs steps in dependency order, streams each result | ~45s |
| Report | Root cause, actions taken, follow-up recommendations | ~5s |

**Total agent time: under 5 minutes vs 45–90 minutes manual.**

At $5,600/minute, that's **$224,000–$476,000 saved per P1 incident.**

### Demo Scenarios

| Scenario | Domain | Clarification needed |
|----------|--------|:-------------------:|
| K8s Crashloop (OOMKilled) | Cloud / Kubernetes | ✓ |
| DB Connection Pool Exhausted | Database | |
| VPN Tunnel Flap (IKE phase 2) | Networking / AWS | |
| SSL Cert Auto-renewal Failure | Security / DNS | |

Each scenario runs in mock mode — no AWS, Datadog, or PagerDuty credentials needed for evaluation.

---

## Architecture

### Full Platform Stack

```
Browser (React 18 + Vite + TypeScript)
    │  EventSource (SSE) · fetch
    ▼
SREDemo Backend (FastAPI · Python 3.13)
    │  SSE stream · REST endpoints
    │  asyncio.Queue per session
    │  Plan History (in-memory + seeded)
    │
    │  POST /invoke · POST /resume
    ▼
AgentGateway (FastAPI · Python 3.13)
    │  RS256 JWT verify (JWKS from AuthService)
    │  Session bind (thread_id → user_id)
    │  Context budget check · compaction · summarisation
    │  GET /models → model registry
    ▼
AgentCore (LangGraph StateGraph)          ←──── RegistryService (FastAPI · PostgreSQL)
    │  9 nodes: intent → clarify →                │  Schema Registry  → extract_intent
    │    entities → plan → HITL →                 │                   → extract_entities
    │    CoT validate → executor →                │  Tool Registry    → plan
    │    execute_step → report                    │  Playbook Registry→ plan
    │  Send API fan-out for parallel steps        │  Versioned · Compatibility-checked
    │  MemorySaver / PostgresSaver                │  ScalableRegistryClient (60s TTL)
    ▼
Claude Sonnet 4.6 (orchestration nodes)
Claude Opus 4.6  (CoT validation — deeper reasoning)

AuthService (FastAPI · PostgreSQL)
    │  RS256 key pair generation · JWT issuance
    │  JWKS endpoint (/.well-known/jwks.json)
    └─→ AgentGateway · RegistryService (JWT verification)
```

### AgentCore Node Graph

```
[User input]
     │
     ▼
[extract_intent] ──(ambiguous?)──► [clarify] ──► loop
     │
     ▼
[extract_entities]
     │
     ▼
[plan]  ◄──────────────────── (modify feedback)
     │
     ▼
[hitl_review] ── interrupt() ── Human approves / modifies / rejects
     │ approve
     ▼
[validate_cot] ── Claude Opus walks DAG, surfaces reasoning
     │ confirm
     ▼
[executor_router] ── Send API fan-out ──► [execute_step × N] (parallel)
     │                                          │
     │◄────────── loop until DAG complete ──────┘
     ▼
[report]
```

### What Runs in Parallel

The planner produces a dependency DAG. The executor automatically fans out steps with no unsatisfied dependencies:

```
Example: 3 AWS checks + 1 PagerDuty incident creation

Tick 1: [describe_vpn_connections] [create_pd_incident]   ← parallel, no dependency
Tick 2: [describe_customer_gateway] [query_dd_metrics]    ← parallel, unblocked by tick 1
Tick 3: [reset_vpn_tunnel × 3]                            ← all use IDs from tick 1
```

No manual parallelism configuration. The framework detects it from the dependency graph.

### Context Window Lifecycle (made visible)

```
Post-plan      ████░░░░░░  40%  green   — planning complete
Early exec     ███████░░░  70%  amber   — WarningBanner slides in
Mid exec       █████████░  92%  red     — WarningBanner turns red
               ↓ COMPACTION #1 ↓        — banner drops, gauge resets to ~30%
Late exec      ████████░░  75%  amber   — filling again
Post exec      █████████░  91%  red
               ↓ COMPACTION #2 ↓        — second reset
Report phase   ██████░░░░  63%  green   — clean finish
```

Every compaction event is summarised by the LLM, entity fidelity is checked, and the summary replaces the raw messages. The user sees this happen in real time.

---

## The Moat

| Moat | Detail |
|------|--------|
| **RegistryService compounds** | Every domain a team registers makes the platform smarter for that team. Versioned schemas, tool contracts, and playbooks accumulate. Competitors starting fresh have none of it. |
| **Plan History compounds** | Every incident resolution becomes a few-shot example for future incidents. The agent improves automatically — no retraining, no manual curation. |
| **HITL as compliance artifact** | Every change is human-approved + timestamped. The audit trail is PCI-DSS / SOC2 / EU AI Act evidence. |
| **Gateway as enterprise gate** | JWT auth + session binding + context budget = the layer a Fortune 500 CISO actually signs off on |
| **DAG safety** | Partial broken configs are structurally impossible — dependencies enforced before execution |
| **Playbook hard rules** | Domain-specific rules validated after planning; a violation rejects the plan before execution — grounded in AWS/SRE docs |
| **Horizontal scale** | DispatchAdapter pattern — switch from Postgres to SQS with one env var, zero code changes |

---

## Market Opportunity

### Primary: Enterprise SRE Automation

- **33,000+** companies with dedicated SRE teams (>100 engineers)
- Average P1 incident cost: **$5,600/minute** (Gartner)
- Average incidents per month per company: **12–40**
- Conservative time savings: **40 minutes per incident**

**TAM: $15B+ annually in incident resolution labour and downtime cost**

### Secondary: MSP Platform (managed service providers)

One MSP engineer manages **10× more customer environments** — the agent handles triage and drafting, the engineer approves. White-label platform licence per site managed.

### Tertiary: Compliance-Adjacent Verticals

Same framework, different playbooks — HIPAA (medical record access), PCI-DSS (payment segmentation), SOX (financial system changes). Zero core changes. New domain = new registry entries.

---

## GTM Strategy

### Phase 1 — Land (Year 1)
- Direct outreach to 50 enterprise DevOps/platform engineering teams
- Free tier: 1 incident scenario, 5 users, community support
- Convert on: Plan History depth (they want their incidents encoded), compliance audit trail
- **Target: 20 paid design partners at $2,000/month = $480K ARR**

### Phase 2 — Expand (Year 2)
- Multi-domain: add network, database, security playbooks
- MSP channel: white-label licensing to top 200 MSPs
- Per-incident pricing tier for high-volume customers
- **Target: $5M ARR**

### Phase 3 — Platform (Year 3)
- **RegistryService GA**: self-serve portal for domain teams to register schemas, tools, playbooks — no engineering ticket required
- Schema versioning + compatibility enforcement unlocks multi-team enterprise deployments (BACKWARD/FORWARD/FULL/BREAKING modes)
- Orchestrator Agent: multi-agent coordination for cross-domain incidents (K8s + DB + network in a single incident thread)
- Governance layer: guard model pre-check, input sanitisation, OTel spans on every LLM call
- **Target: $25M ARR**

---

## Pricing

| Tier | Price | What you get |
|------|-------|-------------|
| **Starter** | $499/month | 3 domains · 10 users · 100 incidents/month · community support |
| **Team** | $1,999/month | 10 domains · 50 users · unlimited incidents · Plan History · SLA |
| **Enterprise** | Custom | Unlimited · on-prem/VPC · RBAC · SSO · custom playbooks · dedicated CSM |
| **MSP** | Per-site licence | White-label · multi-tenant · MSP dashboard |

---

## Traction

- ✅ Full working demo (SREDemo) — 4 incident scenarios, all runnable in `docker compose up`
- ✅ AgentCore: 121 tests, 0 failures, no live DB or LLM required
- ✅ AgentGateway: JWT auth + session binding + context budget management shipped and tested
- ✅ AuthService: RS256 JWT issuance with JWKS endpoint
- ✅ RegistryService: full system design + API design + feature specs complete; Schema Registry, Tool Registry, and Playbook Registry defined; `ScalableRegistryClient` (60s TTL cache) specified in AgentCore
- ✅ React web UI: live SSE streaming, budget gauge, compaction banners, plan history
- ✅ Previous hackathon: HITL + DAG execution demoed and validated with judges

---

## What We're Raising

**Seeking: $1.5M pre-seed**

| Use of funds | % |
|-------------|---|
| Engineering (2 hires: backend + frontend) | 55% |
| Sales & design partner acquisition | 25% |
| Infrastructure & cloud | 10% |
| Legal / compliance certifications | 10% |

**18-month runway.** Milestones: 20 design partners → Series A at $5M ARR.

---

## Why Now

1. **Claude's context window is the new production constraint.** As agents handle longer sessions, context budget management is no longer optional — it's the difference between a working agent and a degraded one. We built the gateway that manages it.

2. **Enterprise HITL is becoming regulatory.** EU AI Act, NIST AI RMF, and SOC2 Type II all point toward mandatory human oversight for consequential AI actions. AgenticFrmk's hard HITL gate is a compliance feature, not a UX choice.

3. **LangGraph has crossed the production threshold.** The primitives (interrupt, Send API, PostgresSaver) now exist to build what we built. 12 months ago this required custom plumbing. Today the framework is stable enough for enterprise deployment.

---

## Team

**Founder** — full-stack systems engineer with background in distributed systems, LLM infrastructure, and enterprise SRE tooling. Built AgenticFrmk end-to-end: framework, gateway, auth, UI, tests, Docker stack.

---

## Contact

mauttaram@gmail.com

GitHub: https://github.com/AgenticFrmk  
Demo: `docker compose up --build` → http://localhost:3000
