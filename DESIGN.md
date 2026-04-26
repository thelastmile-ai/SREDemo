# SRE Demo — VPN Tunnel Flap

> Single scenario. Shows exactly what goes into each registry and how the LLM uses it.

---

## User Query

This is what the SRE types into the agent. It is a simple, natural description — no IDs, no technical details required.

```
Our VPN tunnels to the Boston, New York and Chicago branch offices keep dropping.
Phase 2 keeps renegotiating. ERP and VoIP are degraded, about 450 users affected.
```

The SRE does not know (and should not need to know) the AWS VPN connection IDs, customer gateway ID, or IKE failure codes. The agent discovers those through its first tool calls.

---

## What extract_entities Actually Extracts From This Query

All schema fields are `required: False`. The LLM only fills in what is present in the text. Everything else is `null`.

```
From the query above, extract_entities returns:

  incident_type       = "vpn_tunnel_flap"    ← from "VPN tunnels... keep dropping"
  ike_phase           = "phase2"             ← from "Phase 2 keeps renegotiating"
  affected_branches   = ["Boston",           ← from "Boston, New York and Chicago"
                          "New York",
                          "Chicago"]
  affected_services   = ["ERP", "VoIP"]      ← from "ERP and VoIP are degraded"
  customer_facing     = true                 ← inferred from "450 users affected"
  severity            = "P2"                 ← inferred from impact described

  vpn_connection_ids  = null    ← not in query, discovered by tool call
  customer_gateway_id = null    ← not in query, discovered by tool call
  vpn_gateway         = null    ← not in query, discovered by tool call
  ike_failure_reason  = null    ← not in query, discovered by tool call
  incident_id         = null    ← will be assigned by PagerDuty on creation
```

The null fields are not a problem. The plan's first tool calls exist specifically to discover them.

---

## How the Plan Handles Unknown IDs

The tool contracts allow optional lookup mode:

```python
aws_describe_vpn_connections(
    vpn_connection_ids = None,   # None = list ALL VPN connections in the region
    region             = "us-east-1"
)
# returns all connections → agent identifies the 3 flapping ones from state=DOWN
```

So the DAG becomes a **discovery-then-act** chain:

```
s1: aws_describe_vpn_connections(vpn_connection_ids=None)
    → discovers the 3 affected connection IDs from state=DOWN

s2: aws_describe_customer_gateway(customer_gateway_id from s1 result)
    → discovers cgw ID, BGP config

s3: dd_query_metrics(aws.vpn.tunnel_state, host=vpn-gw-01)
    → confirms flapping pattern

s4: pd_create_incident(...)          ← parallel with s1,s2,s3

s5,s6,s7: aws_reset_vpn_tunnel(each connection_id from s1)
           ← uses IDs discovered in s1, not from the original query
```

The IDs flow through the DAG as step results — not from the entity. The entity provides the **intent and context**. The tools provide the **technical details**.

---

## End-to-End Flow

```
USER QUERY
  │
  │  "3 of our site-to-site VPN tunnels are flapping..."
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE 1 — extract_intent                                          │
│                                                                  │
│ Registry provides:                                               │
│   list_domains()     → ["networking"]                            │
│   get_domain_hints() → {"networking": "network incidents,        │
│                          VPN tunnel flaps, BGP outages..."}      │
│                                                                  │
│ System prompt sent to LLM:                                       │
│   "Valid domains: networking                                     │
│    networking: network incidents, VPN tunnel flaps...            │
│    domain MUST be one of the valid domains listed above."        │
│                                                                  │
│ LLM returns:                                                     │
│   action   = "resolve_vpn_tunnel_flap"                           │
│   domain   = "networking"                                        │
│   ambiguous = false                                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE 2 — extract_entities                                        │
│                                                                  │
│ Registry provides:                                               │
│   get_schema("networking") →                                     │
│     NetworkIncidentEntity fields:                                │
│       incident_id, severity, incident_type,                      │
│       vpn_gateway, vpn_connection_ids,                           │
│       customer_gateway_id, ike_phase,                            │
│       ike_failure_reason, affected_branches,                     │
│       affected_services, customer_facing                         │
│                                                                  │
│ LLM reads the original query + schema → fills what's in text:    │
│   incident_type       = "vpn_tunnel_flap"  ← from query          │
│   severity            = "P2"              ← inferred from impact  │
│   ike_phase           = "phase2"          ← from query           │
│   affected_branches   = ["Boston",        ← from query           │
│                          "New York",                              │
│                          "Chicago"]                               │
│   affected_services   = ["ERP", "VoIP"]   ← from query           │
│   customer_facing     = true              ← inferred             │
│                                                                  │
│   vpn_connection_ids  = null  ← discovered in execute_step s1    │
│   customer_gateway_id = null  ← discovered in execute_step s2    │
│   ike_failure_reason  = null  ← discovered in execute_step s1    │
│   vpn_gateway         = null  ← discovered in execute_step s1    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE 3 — plan                                                    │
│                                                                  │
│ Registry provides:                                               │
│   list_tools("networking") → 8 tool contracts with signatures    │
│   get_playbook("networking") → 5 hard rules + 2 soft rules       │
│                                                                  │
│ System prompt sent to LLM (assembled from registry):             │
│   Available tools:                                               │
│     aws_describe_vpn_connections(vpn_connection_ids, region)     │
│     aws_describe_customer_gateway(customer_gateway_id, region)   │
│     aws_reset_vpn_tunnel(vpn_connection_id, outside_ip, region)  │
│     dd_query_metrics(metric, host, minutes)                      │
│     network_verify_connectivity(source, target, port)            │
│     pd_create_incident(title, severity, body, service_id)        │
│     pd_add_incident_note(incident_id, note)                      │
│     pd_update_incident_status(incident_id, status)               │
│                                                                  │
│   Ordering constraints:                                          │
│     1. Gather tunnel status + metrics BEFORE any reset           │
│     2. Check customer gateway config BEFORE reset                │
│     3. Create PagerDuty incident BEFORE any production change    │
│     4. Verify connectivity AFTER reset, BEFORE closing           │
│     5. Add resolution notes BEFORE marking resolved              │
│                                                                  │
│ LLM returns plan:                                                │
│   s1: aws_describe_vpn_connections  (no deps)  ─┐               │
│   s2: aws_describe_customer_gateway (no deps)   ├─ parallel     │
│   s3: dd_query_metrics              (no deps)   │               │
│   s4: pd_create_incident            (no deps)  ─┘               │
│   s5: aws_reset_vpn_tunnel [Boston] (deps: s1,s2,s3,s4) ─┐     │
│   s6: aws_reset_vpn_tunnel [NYC]    (deps: s1,s2,s3,s4)  ├─ ∥  │
│   s7: aws_reset_vpn_tunnel [Chicago](deps: s1,s2,s3,s4) ─┘     │
│   s8: network_verify_connectivity   (deps: s5,s6,s7)            │
│   s9: pd_add_incident_note          (deps: s8)                   │
│  s10: pd_update_incident_status     (deps: s9)                   │
│                                                                  │
│ Framework validates hard rules:                                  │
│   rule-001: s1,s3 precede s5,s6,s7 ✓                            │
│   rule-002: s2 precedes s5,s6,s7 ✓                              │
│   rule-003: s4 precedes s5,s6,s7 ✓                              │
│   rule-004: s5,s6,s7 precede s8 ✓                               │
│   rule-005: s9 precedes s10 ✓                                    │
│   All rules pass → plan accepted                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE 4 — hitl_review  [PAUSE]                                    │
│                                                                  │
│ SRE sees the plan printed to terminal / UI:                      │
│   Step 1-4: Gather data (parallel)                               │
│   Step 5-7: Reset 3 tunnels (parallel)                           │
│   Step 8:   Verify connectivity                                  │
│   Step 9-10: Update PagerDuty                                    │
│                                                                  │
│ SRE types: "approved"                                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE 5 — validate_cot  (claude-opus-4-6)                        │
│                                                                  │
│ Validates the reasoning chain:                                   │
│   "Phase 1 UP / Phase 2 DOWN → IKE SA negotiation issue.        │
│    Checking customer gateway config before reset is correct —    │
│    a BGP ASN mismatch would make the reset immediately fail.     │
│    Parallel resets are safe — tunnels are independent.           │
│    Connectivity check after reset is required — tunnel can       │
│    show UP in AWS but still drop traffic."                       │
│   → approved                                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE 6 — execute_step  (DAG walk)                                │
│                                                                  │
│ Round 1 (parallel): s1, s3, s4                                   │
│   s1 → aws_describe_vpn_connections(vpn_connection_ids=None)     │
│         DISCOVERS: 3 tunnels Phase1=UP, Phase2=DOWN              │
│         connection IDs: vpn-0a1b, vpn-0f1e, vpn-0b1a            │
│         customer_gateway_id: cgw-0123456789abcdef0               │
│   s3 → dd_query_metrics(aws.vpn.tunnel_state)                    │
│         tunnel_state=0 for all 3, packet_loss=35%                │
│   s4 → pd_create_incident                                        │
│         PD incident "PD-VPN-003" opened, on-call notified        │
│                                                                  │
│ Round 2: s2  (needs cgw_id from s1)                              │
│   s2 → aws_describe_customer_gateway(cgw-0123456789abcdef0)      │
│         BGP ASN 65000, cert valid, static routing                │
│                                                                  │
│ Round 3 (parallel): s5, s6, s7  (use IDs from s1)               │
│   s5 → aws_reset_vpn_tunnel(vpn-0a1b) → Phase2 renegotiating... │
│   s6 → aws_reset_vpn_tunnel(vpn-0f1e) → Phase2 renegotiating... │
│   s7 → aws_reset_vpn_tunnel(vpn-0b1a) → Phase2 renegotiating... │
│                                                                  │
│ Round 3: s8                                                      │
│   s8 → network_verify_connectivity                               │
│         Boston: PASS 0% loss, NYC: PASS 0% loss, Chicago: PASS  │
│                                                                  │
│ Round 4: s9                                                      │
│   s9 → pd_add_incident_note                                      │
│         "Tunnels restored. Root cause: Phase 2 SA lifetime       │
│          mismatch. Recommend aligning IKE lifetime settings."    │
│                                                                  │
│ Round 5: s10                                                     │
│  s10 → pd_update_incident_status → RESOLVED                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ NODE 7 — report                                                  │
│                                                                  │
│ "Incident INC-2024-003 resolved. All 3 IPSec VPN tunnels         │
│  (Boston, New York, Chicago) re-established via DPD reset on     │
│  vpn-gw-01.prod.example.com. 450 remote workers reconnected.     │
│  PagerDuty PD-VPN-003 resolved. Root cause: Phase 2 SA          │
│  lifetime mismatch between VGW and customer gateway.            │
│  Follow-up: align IKE Phase 2 lifetime on cgw-0123456789."       │
└─────────────────────────────────────────────────────────────────┘
```

---

## The Incident

```
INCIDENT INC-2024-003 [P2 - HIGH]
IPSec VPN tunnel flapping — Phase 2 SA re-key failures
VPN gateway: vpn-gw-01.prod.example.com
Tunnels affected:
  vpn-0a1b2c3d4e5f → Boston office  (cgw: 203.0.113.50)
  vpn-0f1e2d3c4b5a → New York office (cgw: 203.0.113.51)
  vpn-0b1a2f3e4d5c → Chicago office  (cgw: 203.0.113.52)
IKE Phase 1: UP on all tunnels
IKE Phase 2: FLAPPING — SA re-key timeout, DPD triggered every 30s
Customer gateway ID: cgw-0123456789abcdef0
Affected services: ERP system (intermittent), VoIP (35% packet loss)
Impact: 450 remote workers intermittently disconnected
```

---

## Registry 1 — Schema Registry

**What it stores:** The shape of the entity the LLM should extract from the incident report.

### Data entered

```python
domain      = "networking"
version     = "v1.0"
description = "network incidents, VPN tunnel flaps, BGP outages, connectivity failures"
owner       = "sre-team"
fields = [
    { name: "incident_id",          type: "str",         required: False },
    { name: "severity",             type: "str",         required: False },  # P1 | P2 | P3
    { name: "incident_type",        type: "str",         required: False },  # vpn_tunnel_flap
    { name: "vpn_gateway",          type: "str",         required: False },
    { name: "vpn_connection_ids",   type: "list[str]",   required: False },
    { name: "customer_gateway_id",  type: "str",         required: False },
    { name: "ike_phase",            type: "str",         required: False },  # phase1 | phase2 | both
    { name: "ike_failure_reason",   type: "str",         required: False },
    { name: "affected_branches",    type: "list[str]",   required: False },
    { name: "affected_services",    type: "list[str]",   required: False },
    { name: "customer_facing",      type: "bool",        required: False },
]
```

### How the LLM uses it

`extract_entities` receives the schema fields and uses `with_structured_output` to force the LLM to fill in exactly those fields from the incident text:

```
System prompt:
  "Extract entities from the conversation matching the NetworkIncidentEntity schema."

LLM reads the incident → returns:
  {
    "incident_id":         "INC-2024-003",
    "severity":            "P2",
    "incident_type":       "vpn_tunnel_flap",
    "vpn_gateway":         "vpn-gw-01.prod.example.com",
    "vpn_connection_ids":  ["vpn-0a1b2c3d4e5f", "vpn-0f1e2d3c4b5a", "vpn-0b1a2f3e4d5c"],
    "customer_gateway_id": "cgw-0123456789abcdef0",
    "ike_phase":           "phase2",
    "ike_failure_reason":  "SA re-key timeout, DPD triggered every 30s",
    "affected_branches":   ["Boston", "New York", "Chicago"],
    "affected_services":   ["ERP system", "VoIP"],
    "customer_facing":     true
  }
```

**Without the registry:** `extract_entities` uses a hardcoded dict → `KeyError` on unknown domain, no versioning, no structured output contract.

**With the registry:** LLM is given a precise schema. Every field is typed. Wrong domain → graceful error, not a crash.

---

## Registry 2 — Tool Registry

**What it stores:** The tools the LLM is allowed to use in its plan, with their signatures and descriptions.

### Data entered (7 tools for this scenario)

```python
[
  ToolContract(
    name="aws_describe_vpn_connections",
    domain="networking",
    description="Query AWS EC2 API to get VPN tunnel state. Returns Phase1/Phase2 status, "
                "DPD timeout counters, last state change timestamp, and outside IP for each tunnel.",
    input_schema={"vpn_connection_ids": "list[str]", "region": "str"},
    output_description="list of tunnel status dicts: {id, phase1, phase2, dpd_timeout, last_changed}",
    version="v1.0", owner="sre-team"
  ),

  ToolContract(
    name="aws_describe_customer_gateway",
    domain="networking",
    description="Fetch customer gateway config from AWS. Returns BGP ASN, outside IP, "
                "certificate validity, and routing type. Use to check config drift before restarting tunnels.",
    input_schema={"customer_gateway_id": "str", "region": "str"},
    output_description="dict: {cgw_id, bgp_asn, outside_ip, certificate_valid, routing_type}",
    version="v1.0", owner="sre-team"
  ),

  ToolContract(
    name="aws_reset_vpn_tunnel",
    domain="networking",
    description="Reset a flapping IPSec VPN tunnel via AWS EC2 ResetVpnTunnelDeadPeerDetection. "
                "Clears DPD counters and forces IKE Phase 2 SA renegotiation. "
                "Safe to run on individual tunnels — does not affect other tunnels.",
    input_schema={"vpn_connection_id": "str", "outside_ip": "str", "region": "str"},
    output_description="dict: {success, new_state, phase2_renegotiating}",
    version="v1.0", owner="sre-team"
  ),

  ToolContract(
    name="dd_query_metrics",
    domain="networking",
    description="Query Datadog metrics API for VPN tunnel health. Use metric "
                "'aws.vpn.tunnel_state' (1=UP, 0=DOWN) and 'aws.vpn.packets_received'. "
                "Returns time-series values for the last N minutes.",
    input_schema={"metric": "str", "host": "str", "minutes": "int"},
    output_description="list of {timestamp, value} data points",
    version="v1.0", owner="sre-team"
  ),

  ToolContract(
    name="network_verify_connectivity",
    domain="networking",
    description="Run end-to-end connectivity test from VPN gateway to branch office subnet. "
                "Performs ICMP ping + TCP port check. Returns latency and packet loss.",
    input_schema={"source": "str", "target": "str", "port": "int"},
    output_description="dict: {reachable, latency_ms, packet_loss_pct}",
    version="v1.0", owner="sre-team"
  ),

  ToolContract(
    name="pd_create_incident",
    domain="networking",
    description="Create a PagerDuty incident via REST API. Notifies the on-call engineer. "
                "Returns incident ID used for subsequent updates.",
    input_schema={"title": "str", "severity": "str", "body": "str", "service_id": "str"},
    output_description="dict: {incident_id, status, assigned_to}",
    version="v1.0", owner="sre-team"
  ),

  ToolContract(
    name="pd_add_incident_note",
    domain="networking",
    description="Add a resolution note to an existing PagerDuty incident. "
                "Use to document what was done, root cause, and follow-up actions.",
    input_schema={"incident_id": "str", "note": "str"},
    output_description="dict: {note_id, created_at}",
    version="v1.0", owner="sre-team"
  ),

  ToolContract(
    name="pd_update_incident_status",
    domain="networking",
    description="Update a PagerDuty incident status. Use 'acknowledged' when work begins, "
                "'resolved' when the incident is closed.",
    input_schema={"incident_id": "str", "status": "str"},
    output_description="dict: {incident_id, status, resolved_at}",
    version="v1.0", owner="sre-team"
  ),

  ToolContract(
    name="aws_check_bgp_status",
    domain="networking",
    description="Check BGP peering state for a VPN connection. Verifies that BGP neighbours "
                "are in Active or Established state after a tunnel reset. A tunnel can show "
                "Phase2=UP in AWS but have BGP in Idle — traffic will not flow until BGP is established.",
    input_schema={"vpn_connection_id": "str", "region": "str"},
    output_description="dict: {vpn_connection_id, bgp_state, prefixes_received, prefixes_advertised}",
    version="v1.0", owner="sre-team"
  ),
]
```

### How the LLM uses it

`plan` receives a formatted tool block injected into the system prompt:

```
Available tools:
  aws_describe_vpn_connections(vpn_connection_ids: list[str], region: str)
      → list of tunnel status dicts: {id, phase1, phase2, dpd_timeout, last_changed}
      Query AWS EC2 API to get VPN tunnel state. Returns Phase1/Phase2 status...

  aws_describe_customer_gateway(customer_gateway_id: str, region: str)
      → dict: {cgw_id, bgp_asn, outside_ip, certificate_valid, routing_type}
      Fetch customer gateway config from AWS...

  aws_reset_vpn_tunnel(vpn_connection_id: str, outside_ip: str, region: str)
      → dict: {success, new_state, phase2_renegotiating}
      Reset a flapping IPSec VPN tunnel via AWS EC2 ResetVpnTunnelDeadPeerDetection...

  dd_query_metrics(metric: str, host: str, minutes: int)
      → list of {timestamp, value} data points
      ...

  network_verify_connectivity(source: str, target: str, port: int)
      → dict: {reachable, latency_ms, packet_loss_pct}
      ...

  pd_create_incident(title: str, severity: str, body: str, service_id: str)
      → dict: {incident_id, status, assigned_to}
      ...

  pd_add_incident_note(incident_id: str, note: str)
      → dict: {note_id, created_at}
      ...

  pd_update_incident_status(incident_id: str, status: str)
      → dict: {incident_id, status, resolved_at}
      ...

tool_name in each step MUST be one of the tools listed above.
```

**Without the registry:** LLM invents tool names from training data — `restart_ipsec_tunnel()`, `check_vpn_health()`, `alert_oncall()` — none of which exist in the codebase. Silent failures at execution time.

**With the registry:** LLM picks from the exact list above. Wrong name → impossible. Signatures are shown, so the LLM generates correct `parameters` for each step.

---

## Registry 3 — Playbook Registry

**What it stores:** Domain-specific ordering rules for the VPN tunnel flap response. The LLM must follow hard rules; soft rules are shown as hints.

### Data entered

```python
Playbook(
  domain="networking",
  version="v1.0",
  owner="sre-team",
  rules=[

    PlaybookRule(
      id="rule-001",
      description="Always gather VPN tunnel status and metrics BEFORE attempting any restart. "
                  "You cannot know which tunnels to reset without first checking their state.",
      before=["aws_describe_vpn_connections", "dd_query_metrics"],
      after=["aws_reset_vpn_tunnel"],
      severity="hard"
    ),

    PlaybookRule(
      id="rule-002",
      description="Check customer gateway config BEFORE restarting tunnels. "
                  "A config mismatch (wrong BGP ASN, expired cert) will cause the restart to fail immediately.",
      before=["aws_describe_customer_gateway"],
      after=["aws_reset_vpn_tunnel"],
      severity="hard"
    ),

    PlaybookRule(
      id="rule-003",
      description="Create a PagerDuty incident BEFORE making any production changes. "
                  "Every tunnel reset must be traceable to an open incident.",
      before=["pd_create_incident"],
      after=["aws_reset_vpn_tunnel"],
      severity="hard"
    ),

    PlaybookRule(
      id="rule-004",
      description="Verify end-to-end connectivity AND BGP peering AFTER tunnel reset, BEFORE closing "
                  "the incident. A tunnel can show Phase2=UP in AWS but still not pass traffic if BGP "
                  "is not in Established state. Both checks are required.",
      before=["aws_reset_vpn_tunnel"],
      after=["network_verify_connectivity", "aws_check_bgp_status"],
      severity="hard"
    ),

    PlaybookRule(
      id="rule-005",
      description="Add resolution notes with root cause BEFORE marking incident resolved. "
                  "Required for post-incident review.",
      before=["pd_add_incident_note"],
      after=["pd_update_incident_status"],
      severity="hard"
    ),

    PlaybookRule(
      id="rule-006",
      description="Verify IKE Phase 1 is UP before diagnosing or resetting Phase 2. "
                  "aws_describe_vpn_connections returns both Phase 1 and Phase 2 state. "
                  "If Phase 1 is DOWN, the root cause is a config mismatch or routing issue — "
                  "a Phase 2 reset will not fix it and must not be attempted.",
      before=["aws_describe_vpn_connections"],
      after=["aws_reset_vpn_tunnel"],
      severity="hard"
    ),

    PlaybookRule(
      id="rule-007",
      description="Initial data gathering steps — describe_vpn, describe_customer_gateway, "
                  "query_metrics — can all run in parallel. They are independent read operations.",
      tools=["aws_describe_vpn_connections", "aws_describe_customer_gateway", "dd_query_metrics"],
      pattern="parallel_allowed",
      severity="soft"
    ),

    PlaybookRule(
      id="rule-008",
      description="Multiple tunnel resets can run in parallel. Each tunnel is independent — "
                  "resetting Boston does not affect New York or Chicago.",
      tools=["aws_reset_vpn_tunnel"],
      pattern="parallel_allowed",
      severity="soft"
    ),
  ]
)
```

### How the LLM uses it

The hard rules are injected into the `plan` system prompt as ordering constraints:

```
Ordering constraints (MUST be respected):
  1. [rule-001] Always gather VPN tunnel status and metrics BEFORE attempting any restart.
               You cannot know which tunnels to reset without first checking their state.
  2. [rule-002] Check customer gateway config BEFORE restarting tunnels.
               A config mismatch will cause the restart to fail immediately.
  3. [rule-003] Create a PagerDuty incident BEFORE making any production changes.
               Every tunnel reset must be traceable to an open incident.
  4. [rule-004] Verify end-to-end connectivity AFTER tunnel reset, BEFORE closing the incident.
               A tunnel can show Phase2=UP but still not pass traffic.
  5. [rule-005] Add resolution notes with root cause BEFORE marking incident resolved.

Hints (optimise for these where possible):
  - aws_describe_vpn_connections, aws_describe_customer_gateway, dd_query_metrics:
    parallel_allowed — independent read operations
  - aws_reset_vpn_tunnel: parallel_allowed — each tunnel is independent
```

After the LLM returns a plan, the framework validates every hard rule:

```
Validate rule-001:
  find all steps where tool_name in ["aws_describe_vpn_connections", "dd_query_metrics"]  → s1, s3
  find all steps where tool_name == "aws_reset_vpn_tunnel"                                → s6, s7, s8
  for each reset step: s1 and s3 must appear in its dependency chain
  s6.dependencies contains s1 ✓,  s3 ✓
  s7.dependencies contains s1 ✓,  s3 ✓
  s8.dependencies contains s1 ✓,  s3 ✓  → PASS

Validate rule-003:
  pd_create_incident step (s5) must appear in dependency chain of every aws_reset_vpn_tunnel step
  s6.dependencies contains s5 ✓
  s7.dependencies contains s5 ✓
  s8.dependencies contains s5 ✓  → PASS
```

If any hard rule is violated, the plan is **rejected** and the LLM is told exactly which rule was broken:

```
"Your plan violates rule-003: aws_reset_vpn_tunnel (step s6) does not depend on
pd_create_incident. Every tunnel reset must be traceable to an open incident.
Please revise the step dependencies."
```

**Without the registry:** LLM may put the PagerDuty step after the reset. No validation catches it. Production changes happen before anyone is paged.

**With the registry:** Hard rule enforced. Impossible to execute a tunnel reset before an incident is open.

---

## What the Full Prompt Looks Like

This is what the `plan` node sends to the LLM after all three registries contribute:

```
You are a task planner. Decompose the user's intent into atomic steps with explicit dependencies.
Each step must declare all steps it depends on by step ID. Steps with no dependencies can run in parallel.

Intent action: resolve_vpn_tunnel_flap
Intent domain: networking
Available entities: {"networking": NetworkIncidentEntity(incident_id="INC-2024-003", ...)}

Available tools:
  aws_describe_vpn_connections(vpn_connection_ids: list[str], region: str)
      → list of tunnel status dicts: {id, phase1, phase2, dpd_timeout, last_changed}
  aws_describe_customer_gateway(customer_gateway_id: str, region: str)
      → dict: {cgw_id, bgp_asn, outside_ip, certificate_valid, routing_type}
  aws_reset_vpn_tunnel(vpn_connection_id: str, outside_ip: str, region: str)
      → dict: {success, new_state, phase2_renegotiating}
  dd_query_metrics(metric: str, host: str, minutes: int)
      → list of {timestamp, value} data points
  network_verify_connectivity(source: str, target: str, port: int)
      → dict: {reachable, latency_ms, packet_loss_pct}
  pd_create_incident(title: str, severity: str, body: str, service_id: str)
      → dict: {incident_id, status, assigned_to}
  pd_add_incident_note(incident_id: str, note: str)
      → dict: {note_id, created_at}
  pd_update_incident_status(incident_id: str, status: str)
      → dict: {incident_id, status, resolved_at}

tool_name in each step MUST be one of the tools listed above.

Ordering constraints (MUST be respected):
  1. [rule-001] Always gather VPN tunnel status and metrics BEFORE attempting any restart.
  2. [rule-002] Check customer gateway config BEFORE restarting tunnels.
  3. [rule-003] Create a PagerDuty incident BEFORE making any production changes.
  4. [rule-004] Verify end-to-end connectivity AFTER tunnel reset, BEFORE closing the incident.
  5. [rule-005] Add resolution notes with root cause BEFORE marking incident resolved.

Hints:
  - aws_describe_vpn_connections, aws_describe_customer_gateway, dd_query_metrics: parallel_allowed
  - aws_reset_vpn_tunnel: parallel_allowed
```

The LLM produces a plan. The framework validates it against the hard rules. If valid, it goes to HITL for SRE approval.

---

## API References

The playbook rules and tool contracts are derived from the following authoritative sources:

### Playbook Rules
| Rule | Derived from |
|------|-------------|
| rule-001 — gather status before reset | [AWS VPN Troubleshooting Guide](https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html) — "Check IKE SA first, then IPsec SA" |
| rule-002 — check CGW config before reset | [AWS VPN Troubleshooting Guide](https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html) — config mismatch is primary root cause |
| rule-003 — create PD incident before changes | Standard SRE change management practice (every production change must be traceable) |
| rule-004 — verify connectivity + BGP after reset | [AWS VPN Troubleshooting Guide](https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html) — BGP peering must be verified after tunnel restoration |
| rule-005 — resolution notes before close | PagerDuty post-incident review requirements |
| rule-006 — Phase 1 UP before Phase 2 reset | [AWS VPN Troubleshooting Guide](https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html) — IKE → IPsec → connectivity sequence is mandatory |

### AWS API Calls
| Tool | AWS API | Reference |
|------|---------|-----------|
| aws_describe_vpn_connections | `ec2.describe_vpn_connections()` | [API Reference](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeVpnConnections.html) |
| aws_describe_customer_gateway | `ec2.describe_customer_gateways()` | [API Reference](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeCustomerGateways.html) |
| aws_reset_vpn_tunnel | `ec2.modify_vpn_tunnel_options(StartupAction='start')` | [API Reference](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyVpnTunnelOptions.html) |
| aws_check_bgp_status | `ec2.describe_vpn_connections()` — `AcceptedRouteCount > 0` as BGP proxy | [VgwTelemetry fields](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_VgwTelemetry.html) |
| dd_query_metrics | Datadog Metrics API v2 | [Datadog VPN Integration](https://docs.datadoghq.com/integrations/amazon_vpn/) |
| network_verify_connectivity | ICMP ping + TCP socket check (stdlib) | — |
| pd_create_incident | [PagerDuty Events API v2](https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI2Nw-send-an-event-to-pager-duty) | — |
| pd_add_incident_note | [PagerDuty REST API — Notes](https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI3Mg-create-a-note-on-an-incident) | — |
| pd_update_incident_status | [PagerDuty REST API — Incidents](https://developer.pagerduty.com/api-reference/b3A6Mjc0ODIwNg-update-an-incident) | — |

### API Behaviour Notes
- `VgwTelemetry.Status` is `UP` or `DOWN` only. Phase 1 vs Phase 2 distinction is in `VgwTelemetry.StatusMessage` (e.g. "IKE phase 1 SA established", "IKE phase 2 SA timeout").
- There is no `ResetVpnConnectionDevice` API. The correct tunnel renegotiation mechanism is `modify_vpn_tunnel_options` with `TunnelOptions={'StartupAction': 'start', 'DPDTimeoutAction': 'restart'}`.
- BGP state (Established/Idle) is not exposed in the EC2 API. `VgwTelemetry.AcceptedRouteCount > 0` is used as the BGP-established proxy — routes are only received when BGP is in Established state.

---

## Requirements Traceability

Every tool in this demo exists because a playbook rule requires it, and every playbook rule exists because an authoritative source mandates it. The full chain for each tool:

---

### aws_describe_vpn_connections

```
Source
  AWS VPN Troubleshooting Guide — Step 1: "Check IKE SA exists on customer gateway"
  https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html
    ↓
Playbook rules satisfied
  rule-001 — gather tunnel status BEFORE reset
             "You cannot know which tunnels to reset without first checking their state"
  rule-006 — verify Phase 1 UP before diagnosing Phase 2
             "If Phase 1 is DOWN, a Phase 2 reset will not fix it"
    ↓
Tool contract
  sre_demo/registries.py — ToolContract(name="aws_describe_vpn_connections", ...)
    ↓
Implementation
  sre_demo/tools/aws_vpn.py — aws_describe_vpn_connections()
  boto3: ec2.describe_vpn_connections()
  API: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeVpnConnections.html
```

---

### aws_describe_customer_gateway

```
Source
  AWS VPN Troubleshooting Guide — "Configuration mismatch is the primary root cause"
  https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html
    ↓
Playbook rule satisfied
  rule-002 — check CGW config BEFORE reset
             "A BGP ASN mismatch or expired certificate will cause reset to fail immediately"
    ↓
Tool contract
  sre_demo/registries.py — ToolContract(name="aws_describe_customer_gateway", ...)
    ↓
Implementation
  sre_demo/tools/aws_vpn.py — aws_describe_customer_gateway()
  boto3: ec2.describe_customer_gateways()
  API: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeCustomerGateways.html
```

---

### aws_reset_vpn_tunnel

```
Source
  AWS ModifyVpnTunnelOptions API — StartupAction='start' forces immediate IKE renegotiation
  https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyVpnTunnelOptions.html
  Note: No ResetVpnConnectionDevice API exists — this is the correct mechanism
    ↓
Playbook rules that must be satisfied BEFORE this tool runs
  rule-001 — tunnel status + metrics gathered first
  rule-002 — customer gateway config checked first
  rule-003 — PagerDuty incident open first
  rule-006 — Phase 1 confirmed UP first
    ↓
Tool contract
  sre_demo/registries.py — ToolContract(name="aws_reset_vpn_tunnel", ...)
    ↓
Implementation
  sre_demo/tools/aws_vpn.py — aws_reset_vpn_tunnel()
  boto3: ec2.modify_vpn_tunnel_options(TunnelOptions={'StartupAction': 'start', 'DPDTimeoutAction': 'restart'})
```

---

### aws_check_bgp_status

```
Source
  AWS VPN Troubleshooting Guide — Step 4: "Check BGP peering — both tunnels must be Active/Established"
  https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html
  AWS VgwTelemetry — AcceptedRouteCount is the only BGP signal available in the EC2 API
  https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_VgwTelemetry.html
    ↓
Playbook rule satisfied
  rule-004 — verify connectivity AND BGP AFTER reset, BEFORE closing
             "A tunnel can show Phase2=UP but BGP Idle means no traffic flows"
    ↓
Tool contract
  sre_demo/registries.py — ToolContract(name="aws_check_bgp_status", ...)
    ↓
Implementation
  sre_demo/tools/aws_vpn.py — aws_check_bgp_status()
  boto3: ec2.describe_vpn_connections() — AcceptedRouteCount > 0 as BGP proxy
  BGP session state is not directly exposed in EC2 API
```

---

### dd_query_metrics

```
Source
  Datadog AWS VPN Integration — aws.vpn.tunnel_state (1=UP, 0=DOWN) metric
  https://docs.datadoghq.com/integrations/amazon_vpn/
  AWS VPN Troubleshooting Guide — quantify impact before reset
    ↓
Playbook rule satisfied
  rule-001 — gather metrics BEFORE reset (parallel with aws_describe_vpn_connections)
             "dd_query_metrics quantifies packet loss to confirm impact"
    ↓
Tool contract
  sre_demo/registries.py — ToolContract(name="dd_query_metrics", ...)
    ↓
Implementation
  sre_demo/tools/datadog.py — dd_query_metrics()
  Datadog Metrics Query API v1: GET /api/v1/query
  API: https://docs.datadoghq.com/api/latest/metrics/#query-timeseries-data
```

---

### network_verify_connectivity

```
Source
  AWS VPN Troubleshooting Guide — Step 3: "Verify tunnel connectivity — ping VGW address
  from customer gateway, confirm firewall rules and tunnel interface IPs"
  https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html
    ↓
Playbook rule satisfied
  rule-004 — verify end-to-end connectivity AFTER reset, BEFORE closing (traffic-plane check)
             "A tunnel can show Phase2=UP in AWS but still not pass traffic"
             Complements aws_check_bgp_status (control-plane check)
    ↓
Tool contract
  sre_demo/registries.py — ToolContract(name="network_verify_connectivity", ...)
    ↓
Implementation
  sre_demo/tools/network_ops.py — network_verify_connectivity()
  Python stdlib: asyncio.create_subprocess_exec("ping", ...) + asyncio.open_connection()
  No external API — standard ICMP + TCP socket check
```

---

### pd_create_incident

```
Source
  Standard SRE change management — every production change must be traceable to an open incident
  PagerDuty Events API v2
  https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI2Nw-send-an-event-to-pager-duty
    ↓
Playbook rule satisfied
  rule-003 — create PD incident BEFORE any production change
             "Every tunnel reset must be traceable to an open incident"
             incident_id returned here is required by pd_add_incident_note and pd_update_incident_status
    ↓
Tool contract
  sre_demo/registries.py — ToolContract(name="pd_create_incident", ...)
    ↓
Implementation
  sre_demo/tools/pagerduty.py — pd_create_incident()
  PagerDuty Events API v2: POST /v2/enqueue
```

---

### pd_add_incident_note

```
Source
  PagerDuty post-incident review requirements — root cause must be documented before closing
  PagerDuty REST API — Notes
  https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI3Mg-create-a-note-on-an-incident
    ↓
Playbook rule satisfied
  rule-005 — add resolution notes BEFORE marking resolved
             "Required for post-incident review. Note must include: what was done,
              root cause, and recommended follow-up actions"
    ↓
Tool contract
  sre_demo/registries.py — ToolContract(name="pd_add_incident_note", ...)
    ↓
Implementation
  sre_demo/tools/pagerduty.py — pd_add_incident_note()
  PagerDuty REST API: POST /incidents/{id}/notes
```

---

### pd_update_incident_status

```
Source
  PagerDuty incident lifecycle — incidents must be explicitly resolved, not left open
  PagerDuty REST API — Incidents
  https://developer.pagerduty.com/api-reference/b3A6Mjc0ODIwNg-update-an-incident
    ↓
Playbook rule satisfied (as the "after" side)
  rule-005 — pd_add_incident_note MUST precede pd_update_incident_status
             "Do not close an incident without a root cause note"
    ↓
Tool contract
  sre_demo/registries.py — ToolContract(name="pd_update_incident_status", ...)
    ↓
Implementation
  sre_demo/tools/pagerduty.py — pd_update_incident_status()
  PagerDuty REST API: PUT /incidents/{id}
```

---

## Summary: What Each Registry Contributes

| Registry | Data entered | What the LLM gets | What it prevents |
|----------|-------------|-------------------|-----------------|
| **Schema Registry** | Field names, types, descriptions for `NetworkIncidentEntity` | Structured output schema — forces extraction of exactly these fields | `KeyError` on unknown domain, free-text extraction, missing fields |
| **Tool Registry** | 8 tool contracts with names, signatures, output descriptions | Tool block in plan prompt — LLM picks from this list only | Invented tool names, wrong parameter types, silent execution failures |
| **Playbook Registry** | 5 hard rules + 2 soft rules with before/after constraints | Ordering constraints in plan prompt + post-plan validation | PD incident skipped, tunnel reset before status check, incident closed without verification |
