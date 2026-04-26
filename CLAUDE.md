# Project: SREDemo

## What this project is
A concrete end-to-end demonstration of the AgentCore framework handling a real AWS Site-to-Site VPN incident. An SRE types a plain English description of the incident — no IDs, no technical details required — and the framework investigates, plans, seeks human approval, validates reasoning, and executes remediation against real AWS, Datadog, and PagerDuty APIs.

This project is a **scenario app**, not a framework. It depends on AgentCore as a pip package and extends it by supplying domain-specific registries (schema, tools, playbook) for the networking domain.

## Tech Stack
- Framework: AgentCore (`git+https://github.com/AgenticFrmk/AgentCore.git@main`) — LangGraph StateGraph, interrupt, Send API
- Auth: AuthService (`http://auth-service:9000`) — RS256 JWT issuance
- Gateway: AgentGateway (`http://agent-gateway:8000`) — JWT verification, session binding
- Checkpointing: LangGraph `MemorySaver` (in-memory — no Postgres needed for demos)
- AWS SDK: boto3 / botocore — EC2 VPN APIs
- HTTP client: httpx — Datadog Metrics API v2, PagerDuty Events API v2 + REST API
- Connectivity checks: Python stdlib asyncio (ICMP ping + TCP socket)
- Env management: python-dotenv
- Container: python:3.13-alpine (GITHUB_TOKEN build secret required for AgentCore dep)

## File Structure

```
SREDemo/
  CLAUDE.md                         — this file
  DESIGN.md                         — full design with registry data and flow diagrams
  README.md                         — setup and run instructions
  Makefile                          — build, up, run, demo, logs, down, clean targets
  docker-compose.yml                — AuthService, AgentGateway, SREDemo containers
  pyproject.toml                    — dependencies (agentcore from GitHub)
  .env.example                      — required environment variables
  sre_demo/
    client.py                       — AgentClient: login, get_models, invoke, resume
    entities.py                     — domain entity schemas (Pydantic, extends EntityBase)
    registries.py                   — build_sre_registry(): schema + tool contracts + playbook
    demo.py                         — CLI runner: calls AgentClient, handles HITL terminal gate
    incidents/
      vpn_tunnel_flap.py            — plain English incident message for the VPN scenario
    tools/
      aws_vpn.py                    — 4 real boto3 EC2 tools
      datadog.py                    — Datadog Metrics Query API v2
      network_ops.py                — ICMP ping + TCP socket connectivity check
      pagerduty.py                  — PagerDuty Events API v2 + REST API
```

## Development Workflow

Every requirement or feature MUST follow this sequence. Never skip a stage or combine stages.

### Stage 1 — Break Requirements Into Small Sections
- Read the relevant design doc or scenario description.
- Split the work into independent sections, each deliverable in a single focused PR.
- A section is "small enough" when it can be reviewed in under 30 minutes and tested in isolation.
- Write the section breakdown as a numbered list before doing anything else. Get agreement before proceeding.

### Stage 2 — Design Doc (one per section)
For each section, produce a design doc under `design/<feature>/` with three parts:

**HLD (High-Level Design)**
- Component diagram (Mermaid) showing what talks to what
- Data flow narrative: input → transformation → output
- Key decisions and tradeoffs (why this approach, not alternatives)
- External dependencies and their contracts

**LLD (Low-Level Design)**
- Class/function signatures with types
- Registry entries: entity fields, tool contracts, playbook rules
- Error handling strategy (what raises, what returns gracefully)
- Config/env vars introduced

**Sequence Diagrams**
- One Mermaid sequence diagram per significant flow
- Must show: demo CLI → AgentGateway → AgentCore graph → tools → response path
- Must show the error path alongside the happy path

### Stage 3 — Design PR
- Open a PR containing ONLY the design doc — no code.
- PR title: `design(<feature>): <what it covers>`
- PR must be reviewed and approved before any implementation starts.
- Design changes discovered during implementation → update the design doc in a follow-up PR, not inline.

### Stage 4 — Implementation (one PR per design section)
- Implement exactly what the approved design doc describes — no scope creep.
- Write tests alongside the code in the same PR (not after):
  - Unit tests for every new tool function
  - Integration test for every new scenario end-to-end (mocked external APIs)
  - Edge cases called out in the LLD error handling section must have corresponding tests
- PR title: `feat(<feature>): <what it implements>`
- PR description must link to the design PR: `Design: #<pr-number>`
- Never open one giant implementation PR for an entire scenario — one PR per design section only.

### Stage 5 — PR Checklist
Before opening any implementation PR verify:
- [ ] All tests pass locally
- [ ] New code has unit tests with edge cases
- [ ] Design doc link included in PR description
- [ ] No scope beyond what the design doc covers
- [ ] Sequence diagrams in design doc still match the implementation

---

## How to work with this project

### Adding a new scenario
1. **Add an incident message** — `sre_demo/incidents/<scenario_name>.py` with a `SCENARIO_MESSAGE` string
2. **Add an entity schema** — new class in `sre_demo/entities.py` extending `EntityBase`; all fields optional
3. **Add tools** — new file(s) in `sre_demo/tools/`; all async; service credentials from env vars
4. **Register in `registries.py`**:
   - Add entity to `SCHEMA_REGISTRY` under a new domain key
   - Add callables to `TOOL_REGISTRY`
   - Add `ToolContract` entries to `_TOOL_CONTRACTS`
   - Add a `Playbook` with hard + soft rules for the new domain
5. **Update `demo.py`** — import and use the new incident message; ensure `_patch_tool_registry()` covers the new tools

### Diagrams
- Always use Mermaid syntax for sequence diagrams
- Always use Mermaid syntax for any other diagrams (flowcharts, ER diagrams, state machines)

### Conventions

#### Entities
- All entity schemas go in `sre_demo/entities.py`
- Extend `agentcore.schemas.entity.EntityBase`
- All fields must be `Optional` (the LLM fills only what is present in the text; IDs are discovered later by tools)
- Set `domain_description` as a class attribute — this is injected into the intent extraction prompt

#### Tools
- Each integration gets its own file in `sre_demo/tools/<integration>.py`
- All tool functions must be `async def`
- Tool functions must accept only JSON-serialisable parameters (str, int, list[str])
- Register every tool in `TOOL_REGISTRY` in `registries.py` — `execute_step` looks up tools by name from this dict
- Tools use service credentials from environment variables — the user's JWT does not flow to external APIs

#### Registry
- All schema entries, tool contracts, and playbook rules live in `registries.py`
- `build_sre_registry()` is the single factory function — pass its return value to `build_graph()`
- `_patch_tool_registry()` in `demo.py` injects SRE tools into the framework's global `TOOL_REGISTRY` before the graph runs — this is required because `execute_step` resolves tool names globally

#### Playbook rules
- Hard rules are validated by the framework after the LLM returns a plan — a violation rejects the plan
- Soft rules are hints injected into the planner prompt — they are not enforced
- Every hard rule must cite its authoritative source in the description (AWS docs, SRE practice, etc.)

---

## How to run

```bash
cd SREDemo
cp .env.example .env   # fill in real credentials
make up                # builds and starts all containers (AuthService, AgentGateway, SREDemo)
make demo              # attach to the running demo container
```

The demo pauses at the HITL gate. Type `approved` to proceed or provide feedback to revise the plan.

## Required environment variables

### Platform connectivity

| Variable | Description |
|----------|-------------|
| `AUTH_SERVICE_URL` | AuthService base URL, e.g. `http://auth-service:9000` |
| `AGENT_API_URL` | AgentGateway base URL, e.g. `http://agent-gateway:8000` |
| `AGENT_USERNAME` | SRE demo user username (used for `POST /auth/token`) |
| `AGENT_PASSWORD` | SRE demo user password |
| `AGENT_LLM_MODEL` | Optional — override model selection (e.g. `claude-opus-4-6`). If absent, first model from `GET /models` is used. |

### Infrastructure

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `AUTH_DB_PASSWORD` | Postgres password for AuthService DB |
| `GATEWAY_DB_PASSWORD` | Postgres password for AgentGateway DB |
| `RSA_KEY_ID` | Key ID for the active RSA key pair (default: `key-2024-01`) |
| `TOKEN_EXPIRE_MINUTES` | JWT TTL in minutes (default: `60`) |
| `GITHUB_TOKEN` | GitHub PAT with repo read scope — needed to pull AgentCore |

### External APIs

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS credentials (or use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | |
| `AWS_DEFAULT_REGION` | Default `us-east-1` |
| `DD_API_KEY` | Datadog API key |
| `DD_APP_KEY` | Datadog application key |
| `DD_SITE` | Datadog site, default `datadoghq.com` |
| `PD_API_KEY` | PagerDuty REST API token |
| `PD_ROUTING_KEY` | PagerDuty Events API v2 integration key |
| `PD_FROM_EMAIL` | PagerDuty user email for API calls |
| `PD_SERVICE_ID` | PagerDuty service ID for incident creation |

## Current scenarios

| Scenario | Domain | Incident file | Entity |
|----------|--------|---------------|--------|
| VPN Tunnel Flap | `networking` | `incidents/vpn_tunnel_flap.py` | `NetworkIncidentEntity` |

## Relationship to other services

SREDemo is a **consumer** of the AgenticFrmk platform. All HTTP calls go through `sre_demo/client.py` (`AgentClient`):

1. `POST {AUTH_SERVICE_URL}/auth/token` — obtain RS256 JWT
2. `GET  {AGENT_API_URL}/models` — fetch supported LLM models (no auth); populate model selector
3. `POST {AGENT_API_URL}/invoke` `{message, llm_model}` + Bearer JWT — start a session; receive `thread_id`
4. `POST {AGENT_API_URL}/resume` `{thread_id, response}` + Bearer JWT — continue after HITL gate

SREDemo does **not** call AgentCore directly at runtime. AgentGateway is the single entry point — it serves `GET /models` from its own `config/models.yaml`, loaded at startup.

SREDemo imports `ToolContract`, `PlaybookRule`, and `EntityBase` from **AgentCore** as a pip package only to define the scenario's registries and entity schemas. `build_graph` and `_patch_tool_registry` are not used — graph execution runs inside AgentGateway/AgentCore, not in-process.
