---
feature: Synthetic Data Layer — VPN Tunnel Flap
solution: SREDemo UI
status: planned
---

# Feature: Synthetic Data Layer

## Purpose
Allow the full AgentCore graph — including all 9 real tool calls — to execute without any AWS, Datadog, or PagerDuty credentials. Pre-canned async functions return realistic, structurally identical responses so the LLM planner and executor behave exactly as in production.

## Inputs
- `USE_SYNTHETIC_DATA` env var (default: `true`)
- Tool registry in `agentcore.tools.registry.TOOL_REGISTRY`

## Outputs
- When `USE_SYNTHETIC_DATA=true`: all tool calls return pre-canned data (see Scenario Data below)
- When `USE_SYNTHETIC_DATA=false`: real tool functions from `sre_demo/tools/` are used unchanged
- No change to tool contracts, playbook rules, or entity schemas — the registry shape is identical

## Scenario: VPN Tunnel Flap

**Initial state (incident start):**
- 3 VPN connections: `vpn-001abc` (Boston), `vpn-002def` (New York), `vpn-003ghi` (Chicago)
- All tunnels: `DOWN`, `IKE phase 2 SA timeout - deleting IPSEC SA`
- Customer gateway `cgw-0abc1234`: BGP ASN `65001`, no certificate drift
- Datadog `aws.vpn.tunnel_state`: drops to `0` at 14:08 UTC; 87% packet loss

**Post-reset state (after `aws_reset_vpn_tunnel`):**
- All tunnels: `UP`, `IKE Phase 2 SA established`
- BGP state: `Established`, 12 prefixes received
- Connectivity: reachable, 0% packet loss, 28ms latency

**PagerDuty:**
- `pd_create_incident` → `PVPNFLAP001`, assigned to `oncall-sre@corp.com`
- `pd_add_incident_note` → `note-001`
- `pd_update_incident_status` → `resolved` at `2026-04-25T14:35:00Z`

## Behaviour
1. `app.py` reads `USE_SYNTHETIC_DATA` at startup.
2. If `true`: `_patch_tools()` replaces every entry in `TOOL_REGISTRY` (both the SRE local registry and the framework's global `agentcore.tools.registry.TOOL_REGISTRY`) with the corresponding function from `synthetic.py`.
3. Synthetic functions mirror the exact same async signature as the real tools (`async def f(...) -> dict`).
4. Each synthetic function includes a small `asyncio.sleep()` delay to simulate real API latency visually.

## File Structure
```
sre_demo/
  synthetic.py    — 9 async functions + SYNTHETIC_TOOL_REGISTRY dict
```

## Synthetic Tool Response Shapes

All response shapes are identical to the real tools — the LLM receives the same JSON structure.

| Tool | Key fields returned |
|------|---------------------|
| `aws_describe_vpn_connections` | `connections[].{vpn_connection_id, state, tunnels[].{outside_ip, status, status_message, ike_phase}}` |
| `aws_describe_customer_gateway` | `customer_gateway.{customer_gateway_id, bgp_asn, routing_type, certificate_arn}` |
| `aws_reset_vpn_tunnel` | `{success, phase2_renegotiating, message}` |
| `aws_check_bgp_status` | `{bgp_state, tunnels[].{bgp_state, prefixes_received}}` |
| `dd_query_metrics` | `{data_points[], summary}` — tunnel_state time-series |
| `network_verify_connectivity` | `{reachable, packet_loss_pct, latency_ms}` |
| `pd_create_incident` | `{incident_id, status, assigned_to}` |
| `pd_add_incident_note` | `{note_id, created_at}` |
| `pd_update_incident_status` | `{status, resolved_at}` |

## Config / Env Vars

| Var | Default | Description |
|-----|---------|-------------|
| `USE_SYNTHETIC_DATA` | `true` | `true` → patch tool registry with synthetic functions |

## Acceptance Criteria
- [ ] `USE_SYNTHETIC_DATA=true` (default): full demo runs with no AWS/Datadog/PagerDuty env vars set
- [ ] All 9 tools return structurally valid responses the LLM can process
- [ ] Synthetic tool calls include a small async sleep so the UI shows realistic timing
- [ ] `USE_SYNTHETIC_DATA=false`: real tools are used without any change to their implementation
- [ ] Tool registry patch happens before the graph starts, not mid-run
- [ ] Docker Compose `sre-demo` service sets `USE_SYNTHETIC_DATA=true` by default

## Future Considerations
- Scenario variants: `SCENARIO=vpn_partial_outage` where only one branch is affected
- Failure injection: `SYNTHETIC_RESET_FAILS=true` to demo the error-path HITL flow
