# AgenticFrmk · SREDemo — Video Narration Script
**Target length: 4–5 minutes  ·  Hackathon + VC submission**

---

## Delivery notes before you record

- Speak at a measured pace — around 130 words per minute.
- The demo MP4 runs ~3.5 minutes of wall time. Your narration adds the business framing before and after.
- Pause naturally at each **[PAUSE]** marker — let the UI breathe.
- Bold lines are the ones that matter most to a judge or VC — slow down and land them.
- Record narration separately and overlay on the MP4, or record screen + mic together.

---

## SECTION 1 — HOOK (0:00 – 0:20)

> It's 3 AM. A P1 alert fires. Payment service is down.
> The on-call SRE gets paged — and spends the next 90 minutes manually
> grepping logs, cross-referencing Datadog, hunting for the right AWS connection ID.
>
> **At $5,600 per minute of downtime, that's a $500,000 event from a single incident.**
>
> AI agents are supposed to fix this. The problem is: every agent framework built today
> is a demo. It works in a notebook. It fails in production.
>
> AgenticFrmk is the infrastructure layer that closes that gap.

---

## SECTION 2 — PLATFORM OVERVIEW (0:20 – 0:40)

*(No UI yet — show the platform architecture slide or title card)*

> AgenticFrmk is a five-service production platform:
> AuthService for RS256 JWT issuance,
> AgentGateway — the production entry point — handling auth, session binding, and context management,
> AgentCore — a nine-node LangGraph StateGraph with 121 tests,
> RegistryService for grounding every LLM call in versioned domain facts,
> and SREDemo — the concrete enterprise use case you're about to see.
>
> Let's walk through a live incident.

---

## SECTION 3 — LOGIN + IDLE DASHBOARD (0:40 – 0:55)

*(UI: login screen → dashboard loads with Plan History visible)*

> The SRE logs in. JWT issued, session bound.
> **[PAUSE]**
>
> The dashboard opens. On the right: Plan History.
> These are real past incident resolutions — stored by the platform.
>
> **This is Plan Memory. And it's about to matter.**

---

## SECTION 4 — INCIDENT SUBMISSION (0:55 – 1:15)

*(UI: chip selected → textarea fills → Ctrl+Enter → agent starts)*

> The SRE selects a pre-set example: Kubernetes pods crashlooping in production.
> OOMKilled. All three replicas down.
>
> One sentence. No alert IDs. No runbook lookup.
> **[PAUSE]**
>
> Submit. The agent starts immediately.

---

## SECTION 5 — CLARIFICATION GATE (1:15 – 1:40)

*(UI: clarification modal appears — "Are the pods crashlooping continuously?")*

> Before the agent commits to a plan, it asks exactly one targeted question.
>
> **This is the first human gate — clarification.**
> Not a prompt failure. Not a hallucination.
> The agent knows what it doesn't know, and it asks.
> **[PAUSE]**
>
> The SRE confirms: all three replicas in CrashLoopBackOff, continuously.
> Submit.

---

## SECTION 6 — PLAN MEMORY / FEW-SHOT (KEY MOMENT) (1:40 – 2:10)

*(UI: activity feed streams node_start/node_done events → Plan History panel lights up with purple badge "Few-shot used by agent")*

> Watch the Plan History panel on the right.
> **[PAUSE — let the badge animate in]**
>
> **There it is. "Few-shot used by agent."**
>
> The platform found a matching historical resolution —
> a previous K8s crashloop, resolved in 287 seconds with a nine-step plan.
>
> **That past resolution is now injected as a few-shot example into the planner's prompt.**
>
> The agent doesn't start from scratch. It starts from proven patterns.
> The longer a customer runs AgenticFrmk, the faster and more accurate it gets —
> on their specific infrastructure.
> **Competitors starting fresh can never replicate this.**

---

## SECTION 7 — HITL APPROVAL (2:10 – 2:40)

*(UI: HITL modal appears — full 9-step DAG displayed with dependencies)*

> The agent has a plan. But it cannot execute a single step without human approval.
>
> **[PAUSE — let the plan steps show]**
>
> This is the second hard gate — HITL plan review.
> The SRE sees every step: describe pods, get logs, query Datadog, create PagerDuty incident,
> update resource limits, rolling restart, verify recovery.
>
> Full dependency graph. Full transparency.
> This isn't a suggestion — **the executor is blocked until the SRE approves.**
>
> Every approval is logged with user identity and timestamp.
> That's your PCI-DSS, SOC2, and EU AI Act audit trail — automatic.
>
> Approve and execute.

---

## SECTION 8 — EXECUTION + CONTEXT BUDGET (2:40 – 3:15)

*(UI: steps stream in with COMPLETED status → budget arc gauge goes amber → red → compaction strip drops)*

> Execution begins. Steps run in parallel where dependencies allow.
>
> Watch the budget gauge in the header — that arc shows real-time token consumption.
>
> **[PAUSE — gauge hits amber]**
>
> Amber. Context is filling. The WarningBanner slides in.
>
> **[PAUSE — gauge hits red, then compaction strip drops from top]**
>
> Context critical — and then: compaction.
>
> AgentGateway automatically evicts 30% of the oldest messages,
> has the LLM summarise what was removed, checks entity fidelity,
> and continues without losing the thread.
>
> **The user sees exactly when the AI's memory was reset. No black box.**
>
> Every step completes: OOMKilled confirmed, memory limits updated to 1.5Gi,
> rolling restart complete, all three pods healthy, PagerDuty resolved.

---

## SECTION 9 — INCIDENT REPORT (3:15 – 3:45)

*(UI: report card appears with ROOT CAUSE, REMEDIATION, FOLLOW-UP)*

> **[PAUSE — let ROOT CAUSE section render]**
>
> Incident resolved. Root cause identified:
> payment-service v3.8.1 introduced an unbounded TransactionCache —
> 1.8 million entries filling the 512Mi memory limit within 8 minutes.
>
> Full remediation log. Follow-up recommendations.
> **Total agent time: under five minutes.**
>
> And the Plan History panel on the right now has a new entry —
> the next K8s incident will find this resolution as its few-shot example.
> **The system just got smarter.**

---

## SECTION 10 — CLOSE (3:45 – 4:15)

*(Return to platform diagram or title card)*

> AgenticFrmk isn't a demo framework wrapped around one use case.
>
> It's five production services:
> JWT authentication, session binding, context budget management,
> a nine-node agent graph with 121 tests,
> versioned domain registries that eliminate LLM hallucination,
> and a Plan Memory layer that makes the agent smarter with every incident.
>
> **Every consequential action is human-approved and timestamped.
> Every LLM call is grounded in registered facts.
> Every context limit is managed and visible.**
>
> This is what production agentic infrastructure looks like.
>
> We're raising $1.5M pre-seed to sign 20 enterprise design partners
> and prove the compounding moat.
>
> **If you want to talk, find me at the conference — or email mauttaram@gmail.com.**
>
> Thank you.

---

## Timing reference

| Section | Wall time | Word count (approx) |
|---------|-----------|---------------------|
| 1 · Hook | 0:00–0:20 | 75 |
| 2 · Platform overview | 0:20–0:40 | 70 |
| 3 · Login + idle | 0:40–0:55 | 55 |
| 4 · Incident submission | 0:55–1:15 | 60 |
| 5 · Clarification gate | 1:15–1:40 | 70 |
| 6 · Plan Memory ⭐ | 1:40–2:10 | 95 |
| 7 · HITL approval | 2:10–2:40 | 100 |
| 8 · Execution + budget | 2:40–3:15 | 105 |
| 9 · Report | 3:15–3:45 | 85 |
| 10 · Close | 3:45–4:15 | 100 |
| **Total** | **~4:15** | **~815 words** |

---

## Key phrases to emphasise (slow down here)

1. **"$5,600 per minute of downtime"** — let it land
2. **"Few-shot used by agent"** — pause before saying this, let the badge animate
3. **"The executor is blocked until the SRE approves"** — compliance hook
4. **"The user sees exactly when the AI's memory was reset"** — trust hook
5. **"Under five minutes"** vs "45–90 minutes manual" — the business case
6. **"The system just got smarter"** — after the report saves to history

---

## Tips for a strong VC take

- Lead with the problem, not the technology — judges and VCs care about the $500K pain, not the LangGraph graph.
- The few-shot moment (Section 6) is the hackathon differentiation — linger on it visually and verbally.
- The compaction strip (Section 8) is the enterprise trust moment — explain it clearly, it's non-obvious.
- End with the ask amount and a human call to action — don't end on "thank you" alone.
