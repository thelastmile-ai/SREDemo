---
feature: Context Budget Display — Animated Token Gauge
solution: SREDemo UI
status: planned
---

# Feature: Context Budget Display

## Purpose
Show the SRE operator (and demo audience) how the context window fills as the conversation grows, and demonstrate the sliding-window compaction feature with a visual animation. This is one of the most technically distinctive aspects of the platform — making it visible and dramatic is a key demo differentiator.

## UI Component: `BudgetGauge`

### Normal state (< 70%)
- Circular arc gauge (Recharts `RadialBarChart`) filling clockwise
- Centre label: `47%` in large bold type
- Below label: `9,400 / 15,000 tokens`
- Colour: `#22c55e` (green)
- Subtle animated shimmer on the filled arc

### Warning state (70–79%)
- Colour transitions to `#eab308` (amber) via CSS transition
- Pulsing outer ring appears
- Toast notification: `⚠ Context budget high — approaching compaction threshold`

### Critical state (≥ 80%) — triggers compaction animation
1. Arc colour turns `#ef4444` (red); ring pulses faster
2. After 0.8s pause: **Compaction Animation**:
   - Arc rapidly drains down (Framer Motion `animate` on the bar value)
   - Particle burst / flash effect on the gauge
   - Arc re-fills to the post-compaction level (e.g. 52%)
   - Colour returns to green
3. Below the gauge: animated badge appears:
   ```
   ↳ Compacted  ·  −20 messages  ·  strategy: sliding_window
   ```
4. Toast notification: `Context compacted — 20 messages evicted, 28% headroom recovered`

### Token counter (below the gauge)
- Live-updating number: `9,400 tokens` ticking up as the conversation grows
- History sparkline: tiny Recharts `LineChart` showing token count per step

## Data Source

Token budget data arrives via the SSE `budget` event emitted by the backend bridge:

```json
{
  "event": "budget",
  "data": {
    "budget_used": 0.84,
    "estimated_tokens": 12600,
    "context_limit": 15000,
    "compacted": false,
    "messages_evicted": 0,
    "strategy": "pass_through"
  }
}
```

The `useAgentStream` hook dispatches this into a `budgetState` slice. `BudgetGauge` reads from this slice and triggers the compaction animation when `compacted` flips from `false` to `true`.

## Demo Context Limit

The backend uses `DEMO_CONTEXT_LIMIT=15000` (default) so the gauge fills visibly during a short demo. The component renders a `[demo mode]` chip below the token count so the audience understands this is a scaled display.

## Token Estimation

The backend computes estimated tokens as `Σ (len(message.content) // 4 + 4)` across all messages in the graph state. No tiktoken dependency — the character-count proxy is sufficient for the demo display.

Simulated compaction is triggered when `budget_used ≥ DEMO_COMPACT_THRESHOLD` (default `0.80`):
- Evict the oldest 30% of messages
- Re-estimate tokens on the reduced list
- Emit a second `budget` event with `compacted=true`

## Config / Env Vars

| Var | Default | Description |
|-----|---------|-------------|
| `DEMO_CONTEXT_LIMIT` | `15000` | Token ceiling used for gauge display only |
| `DEMO_COMPACT_THRESHOLD` | `0.80` | Fraction that triggers simulated compaction |

## Acceptance Criteria

- [ ] Gauge arc fills proportionally to `budget_used`
- [ ] Colour transitions: green → amber at 70%, red at 80%
- [ ] Pulsing ring appears in warning and critical states
- [ ] Compaction animation plays when a `budget` event arrives with `compacted=true`
- [ ] Post-compaction arc level reflects the reduced `budget_used`
- [ ] Compaction badge shows evicted message count and strategy
- [ ] `[demo mode]` chip visible below the token count
- [ ] Token history sparkline updates after each `budget` event
- [ ] Toast notifications fire at warning and compaction events
- [ ] Gauge is visible in the header at all times (not behind a scroll)

## Future Considerations
- Wire to real `ContextBudgetInfo` from AgentGateway HTTP responses once graph integration is complete
- Per-step token delta bars: show how many tokens each tool call added
- Export budget history as a CSV for post-demo analysis
