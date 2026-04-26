---
feature: Clarification HITL Round
solution: SREDemo Hackathon
status: planned
---

# Feature: Clarification HITL Round

## Purpose
After intent extraction, if the incident description is ambiguous, the agent pauses and asks the operator one targeted clarifying question before generating the plan. This demonstrates that the agent is genuinely reasoning about the problem rather than pattern-matching to a fixed playbook.

## User Story
> As a hackathon judge, I want to see the agent pause and ask me a smart follow-up question so I understand it truly comprehends the problem and doesn't blindly execute.

## Clarification Flow

```
extract_intent ──► [ambiguity detected] ──► clarification_needed event
                                                  │
                                         ClarificationModal shown
                                                  │
                                         operator types answer
                                                  │
                                         POST /api/clarify
                                                  │
                                         mock runner resumes ──► plan ──► hitl_review …
```

## Acceptance Criteria

- [ ] The mock runner emits a `clarification_needed` SSE event after intent extraction when `needs_clarification=true` (configurable per script, default `true` for `db_pool` and `k8s_crash` scripts)
- [ ] A `ClarificationModal` slides in (similar UX to `HitlModal`) with the question text and a text input
- [ ] The modal has a **Submit** button; disabled until at least 5 characters typed
- [ ] Submitting calls `POST /api/clarify { session_id, answer }` and closes the modal
- [ ] The mock runner resumes (via a second `asyncio.Event`), incorporates the answer into a `clarification_context` string appended to the entities event payload, then continues to plan
- [ ] The `ActivityFeed` shows a new node entry: `clarify` between `extract_intent` and `plan`
- [ ] If `needs_clarification=false` for the chosen script, the clarification step is skipped entirely — the existing flow is unchanged

## SSE Events

### New: `clarification_needed`
```json
{ "question": "Is this impacting production traffic, or is it isolated to the staging environment?" }
```

### Updated: `entities` (optional field added)
```json
{
  "entities": { ... },
  "clarification_context": "Operator confirmed: production traffic affected across all regions."
}
```

## API Changes

### New: `POST /api/clarify`
```json
// request
{ "session_id": "uuid", "answer": "Production, all three US regions are affected" }

// response
{ "clarified": true }
```

## Per-Script Clarification Questions

| Script | `needs_clarification` | Question |
|--------|-----------------------|----------|
| `vpn_flap` | false | — |
| `db_pool` | true | "Is this affecting a specific service, or all services hitting the database?" |
| `k8s_crash` | true | "Are the pods crashlooping continuously, or did they recover after a restart?" |
| `ssl_expiry` | false | — |

## Out of Scope
- Multi-turn clarification (more than one question per run)
- Real LLM clarification generation
