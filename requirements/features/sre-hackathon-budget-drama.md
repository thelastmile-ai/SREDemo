---
feature: Budget Visibility & Compaction Drama
solution: SREDemo Hackathon
status: planned
---

# Feature: Budget Visibility & Compaction Drama

## Purpose
Make the context budget lifecycle impossible to miss during a live demo. Judges currently have to look at the corner gauge to notice compaction; this feature adds a three-zone colour bar, a sticky warning banner, and a full-width compaction animation so the moment the agent "cleans its memory" is a visible highlight, not a footnote.

## User Story
> As a hackathon judge watching a live demo, I want to visually see the agent's memory filling up and then compacting so I understand the intelligent context management without the presenter having to explain it.

## Visual States

| Budget used | Bar colour | Behaviour |
|-------------|------------|-----------|
| 0–69% | Green | Normal — no warning |
| 70–89% | Amber | Sticky `WarningBanner` slides in at top of dashboard |
| 90–99% | Red | `WarningBanner` intensifies; token counter pulses |
| Compaction fired | — | `CompactionBanner` full-width animated strip plays (4 s) then slides out; budget resets to green |

## Acceptance Criteria

- [ ] Budget bar (`BudgetGauge`) uses three-zone gradient: green → amber (70%) → red (90%)
- [ ] Token counter below gauge shows `12,450 / 15,000 tokens` as text (not just the arc percentage)
- [ ] `WarningBanner` is a sticky bar immediately below the header; it slides down when budget ≥ 70% and is hidden otherwise
- [ ] `WarningBanner` text changes at 90%: "⚠ Context critical — compaction imminent" (red) vs "⚠ Context high — compaction threshold approaching" (amber)
- [ ] `CompactionBanner` is a full-width strip (below header, above content) that animates in when `budget.compacted === true`; shows: "⚡ Context compacted — {N} messages evicted, {M}% headroom recovered"; auto-dismisses after 4 s
- [ ] After compaction the budget bar animates back to the new (lower) percentage with a 0.8 s transition
- [ ] Existing toast notifications for compaction are removed (replaced by the banner)

## Component Changes

### `BudgetGauge` (updated)
- Add token text counter: `{estimated_tokens.toLocaleString()} / {context_limit.toLocaleString()} tokens`
- Arc stroke-color switches based on zone (green/amber/red)

### New: `WarningBanner`
```tsx
interface WarningBannerProps {
  budgetUsed: number   // 0–1
}
// Renders null when budgetUsed < 0.7
// Amber between 0.7–0.9
// Red at 0.9+
```

### New: `CompactionBanner`
```tsx
interface CompactionBannerProps {
  compacted: boolean
  messagesEvicted: number
  headroomRecovered: number  // percentage, derived as (evicted/total * 100)
}
// Slides in from top, 4 s auto-dismiss, Framer Motion
```

## Animation Spec (Framer Motion)

```
CompactionBanner enter:  y: -60 → 0, opacity: 0 → 1, duration: 0.35s ease-out
CompactionBanner exit:   y: 0 → -60, opacity: 1 → 0, duration: 0.35s ease-in, after 4s
BudgetGauge arc reset:   strokeDashoffset animates over 0.8s after compaction
WarningBanner enter:     height: 0 → 44, opacity: 0 → 1, duration: 0.3s
```

## Mock Runner Change
The mock runner already simulates compaction in `_maybe_compact`. The budget event at the end of execution must emit `compacted: true` and `messages_evicted: N > 0` to trigger the new UI state. Adjust the token accumulation in `_run_demo_mock` so budget reliably crosses 70% during execution (approx 10,500 tokens) and compaction fires at the end.

## Out of Scope
- Real token counting via Anthropic token counting API
- Per-message granular timeline of budget growth
