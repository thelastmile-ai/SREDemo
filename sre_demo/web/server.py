"""
SREDemo FastAPI backend bridge.

Runs AgentCore in-process, streams real-time agent events to the React
frontend via Server-Sent Events, and exposes REST endpoints for login,
demo start, HITL approval, clarification, and plan history.

Environment variables:
  SERVER_PORT            default 3000
  USE_SYNTHETIC_DATA     default true  — patch tools with synthetic functions
  USE_MOCK_LLM           default false — skip AgentCore; emit pre-scripted events
  DEMO_CONTEXT_LIMIT     default 15000
  DEMO_COMPACT_THRESHOLD default 0.80
  ANTHROPIC_API_KEY      required when USE_MOCK_LLM=false
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── AgentCore imports (installed from local source in Docker; lazy-guarded) ──
try:
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    from agentcore.graph.builder import build_graph
    from agentcore.llm.config import default_anthropic_config
    import agentcore.tools.registry as _fw_registry
    from sre_demo.registries import build_sre_registry, TOOL_REGISTRY as _SRE_REGISTRY
    _AGENTCORE_AVAILABLE = True
except ImportError:
    _AGENTCORE_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
SERVER_PORT = int(os.getenv("SERVER_PORT", "3000"))
USE_SYNTHETIC = os.getenv("USE_SYNTHETIC_DATA", "true").lower() == "true"
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
DEMO_CONTEXT_LIMIT = int(os.getenv("DEMO_CONTEXT_LIMIT", "15000"))
DEMO_COMPACT_THRESHOLD = float(os.getenv("DEMO_COMPACT_THRESHOLD", "0.80"))


# ── Script bundles ────────────────────────────────────────────────────────────

@dataclass
class ScriptBundle:
    script_key: str
    domain: str
    steps: list[dict]
    step_outputs: dict[str, Any]
    report: str
    entities: dict
    step_delays: list[float]
    needs_clarification: bool = False
    clarification_question: str = ""


# ── VPN Tunnel Flap ───────────────────────────────────────────────────────────

_VPN_STEPS = [
    {"id": "step_1",  "tool": "aws_describe_vpn_connections",  "dependencies": [],                       "status": "PENDING"},
    {"id": "step_2",  "tool": "aws_describe_customer_gateway", "dependencies": ["step_1"],               "status": "PENDING"},
    {"id": "step_3",  "tool": "dd_query_metrics",              "dependencies": ["step_1"],               "status": "PENDING"},
    {"id": "step_4",  "tool": "pd_create_incident",            "dependencies": ["step_1"],               "status": "PENDING"},
    {"id": "step_5",  "tool": "aws_reset_vpn_tunnel",          "dependencies": ["step_2", "step_4"],     "status": "PENDING"},
    {"id": "step_6",  "tool": "aws_reset_vpn_tunnel",          "dependencies": ["step_2", "step_4"],     "status": "PENDING"},
    {"id": "step_7",  "tool": "aws_reset_vpn_tunnel",          "dependencies": ["step_2", "step_4"],     "status": "PENDING"},
    {"id": "step_8",  "tool": "network_verify_connectivity",   "dependencies": ["step_5", "step_6", "step_7"], "status": "PENDING"},
    {"id": "step_9",  "tool": "aws_check_bgp_status",          "dependencies": ["step_5"],               "status": "PENDING"},
    {"id": "step_10", "tool": "pd_add_incident_note",          "dependencies": ["step_8"],               "status": "PENDING"},
    {"id": "step_11", "tool": "pd_update_incident_status",     "dependencies": ["step_10"],              "status": "PENDING"},
]

_VPN_OUTPUTS: dict[str, Any] = {
    "step_1":  {"connections": [{"vpn_connection_id": "vpn-0a1b2c3d", "branch": "Boston",   "tunnels": [{"status": "DOWN"}, {"status": "DOWN"}]}, {"vpn_connection_id": "vpn-0e4f5a6b", "branch": "New York", "tunnels": [{"status": "DOWN"}, {"status": "UP"}]}, {"vpn_connection_id": "vpn-0c7d8e9f", "branch": "Chicago", "tunnels": [{"status": "DOWN"}, {"status": "DOWN"}]}]},
    "step_2":  {"customer_gateway_id": "cgw-boston-01", "ip_address": "203.0.113.1", "bgp_asn": "65001", "device_type": "Cisco ASA 5505"},
    "step_3":  {"series": [{"metric": "aws.vpn.tunnel_state", "display_name": "VPN Tunnel State"}], "status": "ok"},
    "step_4":  {"incident_id": "PD-82741", "status": "triggered", "html_url": "https://acme.pagerduty.com/incidents/Q1A2B3C4D5"},
    "step_5":  {"vpn_connection_id": "vpn-0a1b2c3d", "outside_ip": "203.0.113.10", "status": "succeeded", "new_state": "UP", "message": "Tunnel reset. Phase 2 SA re-established."},
    "step_6":  {"vpn_connection_id": "vpn-0e4f5a6b", "outside_ip": "198.51.100.20", "status": "succeeded", "new_state": "UP", "message": "Tunnel reset. Lifetime standardised to 28800s."},
    "step_7":  {"vpn_connection_id": "vpn-0c7d8e9f", "outside_ip": "192.0.2.30",    "status": "succeeded", "new_state": "UP", "message": "Tunnel reset. Transform AES-256 confirmed."},
    "step_8":  {"target": "erp.boston.corp", "reachable": True, "latency_ms": 4.2},
    "step_9":  {"vpn_connection_id": "vpn-0a1b2c3d", "bgp_status": "established", "prefixes_received": 4},
    "step_10": {"incident_id": "PD-82741", "note_id": "NOTE-441", "status": "added"},
    "step_11": {"incident_id": "PD-82741", "status": "resolved", "updated": True},
}

_VPN_REPORT = """\
INCIDENT RESOLVED — VPN Tunnel Flap (P2)
=========================================
Affected: Boston, New York, Chicago branch offices
Users impacted: ~450 (ERP + VoIP)

ROOT CAUSE
----------
Phase 2 IKE lifetime mismatch between AWS Virtual Private Gateway (28800s)
and branch CPE devices (3600s on Chicago PA-220, 3600s on Boston/NY ASA 5505).
DPD timeout cascades caused all Phase 2 SAs to be torn down simultaneously
during a scheduled rekey window at 14:32 UTC.

REMEDIATION
-----------
1. Discovered 3 VPN connections (vpn-0a1b2c3d, vpn-0e4f5a6b, vpn-0c7d8e9f)
   with 5/6 tunnels in DOWN state via aws_describe_vpn_connections.
2. Confirmed Cisco ASA 5505 (Boston/NY) and Palo Alto PA-220 (Chicago) as CPE.
3. Reset all 3 tunnel pairs via ModifyVpnTunnelOptions with standardised
   Phase 2 lifetime 28800s and DPDTimeoutAction=restart.
4. Verified BGP re-established (4 prefixes received) and ERP reachable (4.2ms).

FOLLOW-UP
---------
- Align Phase 2 lifetime config on all CPE devices to 28800s to prevent recurrence.
- Add Datadog alert: aws.vpn.tunnel_state < 1 for > 60s → page on-call SRE.
"""

_VPN_ENTITIES = {
    "networking": {
        "incident_type": "vpn_tunnel_flap",
        "severity": "P2",
        "ike_phase": "phase2",
        "affected_branches": ["Boston", "New York", "Chicago"],
        "affected_services": ["ERP", "VoIP"],
        "customer_facing": True,
    }
}

_SCRIPT_VPN = ScriptBundle(
    script_key="vpn_flap",
    domain="networking",
    steps=_VPN_STEPS,
    step_outputs=_VPN_OUTPUTS,
    report=_VPN_REPORT,
    entities=_VPN_ENTITIES,
    step_delays=[0.7, 0.5, 0.8, 0.6, 1.3, 1.2, 1.2, 0.9, 0.6, 0.4, 0.4],
    needs_clarification=False,
)


# ── DB Connection Pool Exhaustion ─────────────────────────────────────────────

_DB_STEPS = [
    {"id": "step_1", "tool": "pg_describe_pool_status",     "dependencies": [],                   "status": "PENDING"},
    {"id": "step_2", "tool": "dd_query_metrics",            "dependencies": ["step_1"],           "status": "PENDING"},
    {"id": "step_3", "tool": "pd_create_incident",          "dependencies": ["step_1"],           "status": "PENDING"},
    {"id": "step_4", "tool": "pg_kill_idle_connections",    "dependencies": ["step_2", "step_3"], "status": "PENDING"},
    {"id": "step_5", "tool": "k8s_scale_deployment",        "dependencies": ["step_4"],           "status": "PENDING"},
    {"id": "step_6", "tool": "pg_adjust_pool_config",       "dependencies": ["step_4"],           "status": "PENDING"},
    {"id": "step_7", "tool": "network_verify_connectivity", "dependencies": ["step_5", "step_6"], "status": "PENDING"},
    {"id": "step_8", "tool": "pd_update_incident_status",   "dependencies": ["step_7"],           "status": "PENDING"},
]

_DB_OUTPUTS: dict[str, Any] = {
    "step_1": {"pool_name": "checkout-pool", "max_conn": 100, "active": 99, "idle": 1, "waiting": 47, "database": "orders-db"},
    "step_2": {"series": [{"metric": "postgresql.connections", "max_value": 99, "trend": "linear_increase_since_09:42"}], "status": "ok"},
    "step_3": {"incident_id": "PD-91043", "status": "triggered", "html_url": "https://acme.pagerduty.com/incidents/Q9X8Y7Z6"},
    "step_4": {"killed": 34, "kill_criteria": "idle > 5min", "remaining_active": 65, "waiting": 0},
    "step_5": {"deployment": "checkout-service", "namespace": "prod", "previous_replicas": 3, "new_replicas": 5, "ready": 5},
    "step_6": {"pool_name": "checkout-pool", "previous_max_conn": 100, "new_max_conn": 150, "applied": True},
    "step_7": {"target": "checkout.prod.svc.cluster.local", "reachable": True, "latency_ms": 2.1, "status_code": 200},
    "step_8": {"incident_id": "PD-91043", "status": "resolved", "updated": True},
}

_DB_REPORT = """\
INCIDENT RESOLVED — PostgreSQL Connection Pool Exhaustion (P2)
==============================================================
Service: checkout-service (prod)
Database: orders-db (PostgreSQL 15.4, PgBouncer pool)
Users impacted: ~200 (checkout flow blocked)

ROOT CAUSE
----------
checkout-service v2.14.3 (deployed 09:42 UTC) introduced an unintentional
connection leak — HTTP handlers were not releasing connections back to the pool
after request completion. Within 90 minutes the 100-connection PgBouncer pool
reached 99/100 active with 47 checkout requests queuing for connections.

REMEDIATION
-----------
1. Confirmed pool exhaustion via pg_describe_pool_status: 99/100 active, 47 waiting.
2. Datadog confirmed linear connection ramp starting at deploy time 09:42 UTC.
3. Created PagerDuty incident PD-91043, severity P2.
4. Killed 34 idle connections (idle > 5 min), freeing immediate capacity.
5. Scaled checkout-service 3 → 5 replicas to reduce per-replica connection demand.
6. Increased PgBouncer pool_size 100 → 150 as temporary headroom buffer.
7. Verified checkout API reachable and latency normalised to 2.1ms.

FOLLOW-UP
---------
- Roll back v2.14.3 or patch connection leak in checkout-service.
- Add PgBouncer alert: pool usage > 80% → page on-call SRE.
- Set idle_in_transaction_session_timeout = 30s on orders-db.
"""

_DB_ENTITIES = {
    "database": {
        "incident_type": "connection_pool_exhaustion",
        "severity": "P2",
        "service": "checkout-service",
        "database": "PostgreSQL",
        "pool_max": 100,
        "active_connections": 99,
        "waiting_queries": 47,
        "customer_facing": True,
    }
}

_SCRIPT_DB = ScriptBundle(
    script_key="db_pool",
    domain="database",
    steps=_DB_STEPS,
    step_outputs=_DB_OUTPUTS,
    report=_DB_REPORT,
    entities=_DB_ENTITIES,
    step_delays=[0.7, 0.8, 0.5, 1.0, 1.1, 0.9, 0.7, 0.4],
    needs_clarification=True,
    clarification_question="Is this affecting a specific service, or all services that connect to the database?",
)


# ── Kubernetes Pod Crashloop ───────────────────────────────────────────────────

_K8S_STEPS = [
    {"id": "step_1", "tool": "k8s_describe_pods",          "dependencies": [],                   "status": "PENDING"},
    {"id": "step_2", "tool": "k8s_get_pod_logs",           "dependencies": ["step_1"],           "status": "PENDING"},
    {"id": "step_3", "tool": "dd_query_metrics",           "dependencies": ["step_1"],           "status": "PENDING"},
    {"id": "step_4", "tool": "pd_create_incident",         "dependencies": ["step_1"],           "status": "PENDING"},
    {"id": "step_5", "tool": "k8s_update_resource_limits", "dependencies": ["step_2", "step_3"], "status": "PENDING"},
    {"id": "step_6", "tool": "k8s_restart_deployment",     "dependencies": ["step_5"],           "status": "PENDING"},
    {"id": "step_7", "tool": "k8s_describe_pods",          "dependencies": ["step_6"],           "status": "PENDING"},
    {"id": "step_8", "tool": "k8s_get_events",             "dependencies": ["step_6"],           "status": "PENDING"},
    {"id": "step_9", "tool": "pd_update_incident_status",  "dependencies": ["step_7", "step_8"], "status": "PENDING"},
]

_K8S_OUTPUTS: dict[str, Any] = {
    "step_1": {"pods": [{"name": "payment-service-7d9f8b-xkl2p", "status": "CrashLoopBackOff", "restarts": 17, "reason": "OOMKilled"}, {"name": "payment-service-7d9f8b-mn4qr", "status": "CrashLoopBackOff", "restarts": 14, "reason": "OOMKilled"}, {"name": "payment-service-7d9f8b-jp9wt", "status": "CrashLoopBackOff", "restarts": 15, "reason": "OOMKilled"}]},
    "step_2": {"container": "payment-service", "last_lines": ["FATAL OOMKilled at heap 512Mi", "TransactionCache size: 1,847,293 entries", "java.lang.OutOfMemoryError: Java heap space"]},
    "step_3": {"series": [{"metric": "kubernetes.memory.usage", "trend": "linear_increase", "peak_mi": 511, "limit_mi": 512}], "status": "ok"},
    "step_4": {"incident_id": "PD-73821", "status": "triggered", "html_url": "https://acme.pagerduty.com/incidents/P7Q8R9S0"},
    "step_5": {"deployment": "payment-service", "namespace": "prod", "memory_limit_before": "512Mi", "memory_limit_after": "1536Mi", "memory_request_after": "512Mi", "applied": True},
    "step_6": {"deployment": "payment-service", "namespace": "prod", "strategy": "RollingUpdate", "status": "completed", "ready_replicas": 3},
    "step_7": {"pods": [{"name": "payment-service-8e0a1b-vrt3k", "status": "Running", "restarts": 0, "ready": True}, {"name": "payment-service-8e0a1b-qwx9y", "status": "Running", "restarts": 0, "ready": True}, {"name": "payment-service-8e0a1b-zab6c", "status": "Running", "restarts": 0, "ready": True}]},
    "step_8": {"events": [{"type": "Normal", "reason": "Pulled", "message": "Successfully pulled image"}, {"type": "Normal", "reason": "Started", "message": "Started container payment-service"}], "oom_events_last_10min": 0},
    "step_9": {"incident_id": "PD-73821", "status": "resolved", "updated": True},
}

_K8S_REPORT = """\
INCIDENT RESOLVED — Kubernetes Pod Crashloop / OOMKilled (P2)
=============================================================
Service: payment-service (prod namespace, eks-prod-us-east-1)
Users impacted: ~80 (payment processing unavailable)

ROOT CAUSE
----------
payment-service v3.8.1 introduced an unbounded in-memory TransactionCache.
Under load test traffic (Black Friday prep), each pod accumulated 1.8M cache
entries consuming the full 512Mi memory limit within 8 minutes, triggering
OOMKilled termination and CrashLoopBackOff across all 3 replicas.

REMEDIATION
-----------
1. Described pods: 3/3 in CrashLoopBackOff, restart counts 14–17.
2. Retrieved crash logs: OOMKilled confirmed, TransactionCache at 1.8M entries.
3. Datadog memory metrics confirmed linear growth from load test start.
4. Created PagerDuty incident PD-73821.
5. Updated memory limit 512Mi → 1.5Gi, request 256Mi → 512Mi.
6. Triggered rolling restart — all 3 pods healthy within 4 minutes.
7. Verified 0 OOMKilled events in last 10 minutes via k8s_get_events.

FOLLOW-UP
---------
- Add LRU eviction to TransactionCache (max 100k entries).
- Set pod memory alert: > 80% of limit → page on-call SRE.
- Add memory regression test to CI pipeline before prod deploy.
"""

_K8S_ENTITIES = {
    "kubernetes": {
        "incident_type": "pod_crashloop",
        "severity": "P2",
        "service": "payment-service",
        "namespace": "prod",
        "crash_reason": "OOMKilled",
        "affected_pods": 3,
        "restart_count": 17,
        "customer_facing": True,
    }
}

_SCRIPT_K8S = ScriptBundle(
    script_key="k8s_crash",
    domain="kubernetes",
    steps=_K8S_STEPS,
    step_outputs=_K8S_OUTPUTS,
    report=_K8S_REPORT,
    entities=_K8S_ENTITIES,
    step_delays=[0.8, 1.0, 0.7, 0.5, 1.2, 1.5, 0.8, 0.6, 0.4],
    needs_clarification=True,
    clarification_question="Are the pods crashlooping continuously, or did they recover after a manual restart?",
)


# ── SSL Certificate Expiry ────────────────────────────────────────────────────

_SSL_STEPS = [
    {"id": "step_1", "tool": "ssl_check_certificate",   "dependencies": [],           "status": "PENDING"},
    {"id": "step_2", "tool": "pd_create_incident",       "dependencies": ["step_1"],   "status": "PENDING"},
    {"id": "step_3", "tool": "acm_request_certificate",  "dependencies": ["step_1"],   "status": "PENDING"},
    {"id": "step_4", "tool": "acm_validate_dns",         "dependencies": ["step_3"],   "status": "PENDING"},
    {"id": "step_5", "tool": "nginx_reload_config",      "dependencies": ["step_4"],   "status": "PENDING"},
    {"id": "step_6", "tool": "ssl_verify_certificate",   "dependencies": ["step_5"],   "status": "PENDING"},
    {"id": "step_7", "tool": "pd_update_incident_status","dependencies": ["step_6"],   "status": "PENDING"},
]

_SSL_OUTPUTS: dict[str, Any] = {
    "step_1": {"domain": "api.acme.com", "issuer": "Let's Encrypt", "expired_at": "2026-04-26T00:00:00Z", "days_expired": 0, "tls_version": "TLSv1.3", "error": "certificate has expired"},
    "step_2": {"incident_id": "PD-55209", "status": "triggered", "severity": "P1", "html_url": "https://acme.pagerduty.com/incidents/SSL0001"},
    "step_3": {"certificate_arn": "arn:aws:acm:us-east-1:123456789:certificate/abc-123", "domain": "api.acme.com", "status": "PENDING_VALIDATION", "validation_method": "DNS"},
    "step_4": {"record_name": "_acme-challenge.api.acme.com", "record_value": "abc123xyz789", "propagated": True, "propagation_seconds": 47, "certificate_status": "ISSUED"},
    "step_5": {"config_test": "OK", "reload_signal": "sent", "workers_gracefully_restarted": 4, "new_cert_loaded": True},
    "step_6": {"domain": "api.acme.com", "issuer": "Let's Encrypt", "valid_from": "2026-04-26", "valid_to": "2026-07-25", "days_remaining": 90, "tls_version": "TLSv1.3", "chain_valid": True},
    "step_7": {"incident_id": "PD-55209", "status": "resolved", "updated": True},
}

_SSL_REPORT = """\
INCIDENT RESOLVED — SSL Certificate Expiry (P1)
===============================================
Domain: api.acme.com
Certificate Authority: Let's Encrypt
Users impacted: ~1,200 (all API clients receiving TLS handshake errors)

ROOT CAUSE
----------
The Let's Encrypt auto-renewal cron job on api-gateway-01 silently failed
on 2026-04-25 due to a DNS propagation delay during a Route 53 zone transfer.
The certificate expired at 00:00 UTC today — 7 days after the failed renewal.
No monitoring alert was configured for certificate expiry < 14 days.

REMEDIATION
-----------
1. Confirmed cert expiry: api.acme.com expired at 2026-04-26T00:00:00Z.
2. Created PagerDuty incident PD-55209, severity P1.
3. Issued new 90-day Let's Encrypt certificate via ACM DNS challenge.
4. DNS TXT record validated in 47 seconds via Route 53.
5. Reloaded nginx — zero-downtime cert swap (4 workers gracefully restarted).
6. Verified: new cert valid 2026-04-26 → 2026-07-25, TLS 1.3, chain valid.

FOLLOW-UP
---------
- Add CloudWatch alarm: ACM certificate days to expiry < 30 → PagerDuty.
- Add Datadog synthetic: check api.acme.com TLS cert every 5 minutes.
- Migrate all manual renewals to AWS Certificate Manager auto-renewal.
"""

_SSL_ENTITIES = {
    "security": {
        "incident_type": "ssl_cert_expiry",
        "severity": "P1",
        "domain": "api.acme.com",
        "issuer": "Let's Encrypt",
        "expired_at": "2026-04-26T00:00:00Z",
        "customer_facing": True,
        "users_impacted": 1200,
    }
}

_SCRIPT_SSL = ScriptBundle(
    script_key="ssl_expiry",
    domain="security",
    steps=_SSL_STEPS,
    step_outputs=_SSL_OUTPUTS,
    report=_SSL_REPORT,
    entities=_SSL_ENTITIES,
    step_delays=[0.6, 0.4, 1.2, 1.8, 0.9, 0.7, 0.3],
    needs_clarification=False,
)


# ── Script dispatch ───────────────────────────────────────────────────────────

_SCRIPTS: dict[str, ScriptBundle] = {
    "vpn_flap":  _SCRIPT_VPN,
    "db_pool":   _SCRIPT_DB,
    "k8s_crash": _SCRIPT_K8S,
    "ssl_expiry": _SCRIPT_SSL,
}

_KEYWORD_MAP: list[tuple[list[str], str]] = [
    (["vpn", "tunnel", "bgp", "ipsec", "ike", "branch office", "site-to-site"], "vpn_flap"),
    (["db", "database", "connection pool", "postgres", "sql", "pg ", "checkout", "too many connections"], "db_pool"),
    (["k8s", "kubernetes", "pod", "crashloop", "oom", "evicted", "container", "namespace", "payment"], "k8s_crash"),
    (["ssl", "cert", "tls", "expir", "https", "certificate", "acm", "handshake"], "ssl_expiry"),
]


def _dispatch_script(message: str) -> ScriptBundle:
    lower = message.lower()
    for keywords, key in _KEYWORD_MAP:
        if any(kw in lower for kw in keywords):
            return _SCRIPTS[key]
    return _SCRIPTS["vpn_flap"]


# ── Plan history store ────────────────────────────────────────────────────────

@dataclass
class HistoryEntry:
    id: str
    action: str
    domain: str
    description: str
    outcome: str
    steps_count: int
    resolved_at: str
    duration_seconds: int
    few_shot_used: bool = False


_history_store: list[HistoryEntry] = []


def _seed_history() -> None:
    _history_store.extend([
        HistoryEntry("hist-001", "resolve_vpn_flap", "networking",
                     "VPN tunnel flap — Boston/NY/Chicago (IKE phase 2 lifetime mismatch)",
                     "COMPLETED", 11, "2026-04-25T14:32:00Z", 342),
        HistoryEntry("hist-002", "resolve_db_pool", "database",
                     "PostgreSQL connection pool exhausted — checkout-service (leak in v2.14.3)",
                     "COMPLETED", 8, "2026-04-25T09:15:00Z", 218),
        HistoryEntry("hist-003", "resolve_k8s_crash", "kubernetes",
                     "payment-service pods OOMKilled in prod — TransactionCache unbounded growth",
                     "COMPLETED", 9, "2026-04-25T22:47:00Z", 287),
        HistoryEntry("hist-004", "resolve_ssl_expiry", "security",
                     "SSL cert expired on api.acme.com — auto-renewal cron silent failure",
                     "FAILED", 4, "2026-04-25T11:03:00Z", 95),
    ])


def _find_few_shot_match(bundle: ScriptBundle) -> HistoryEntry | None:
    """Return the most recent COMPLETED history entry whose action matches the current script."""
    target_action = f"resolve_{bundle.script_key}"
    for entry in reversed(_history_store):
        if entry.outcome == "COMPLETED" and entry.action == target_action:
            return entry
    return None


# ── Session model ─────────────────────────────────────────────────────────────

@dataclass
class DemoSession:
    session_id: str
    username: str
    message: str = ""
    script: ScriptBundle | None = None
    start_time: float = field(default_factory=time.time)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    hitl_event: asyncio.Event = field(default_factory=asyncio.Event)
    hitl_response: str | None = None
    clarify_event: asyncio.Event = field(default_factory=asyncio.Event)
    clarify_answer: str | None = None
    task: asyncio.Task | None = None


_sessions: dict[str, DemoSession] = {}


# ── Budget helpers ─────────────────────────────────────────────────────────────

def _estimate_tokens(messages: list[Any]) -> int:
    total = 0
    for m in messages:
        if hasattr(m, "content"):
            content = m.content
        elif isinstance(m, dict):
            content = m.get("content", "")
        else:
            content = str(m)
        total += len(str(content)) // 4 + 4
    return total


def _synthetic_msgs(n_tokens: int) -> list[dict]:
    return [{"content": "x" * 4} for _ in range(max(1, n_tokens // 4))]


def _build_budget_event(messages: list[Any], compacted: bool = False, messages_evicted: int = 0) -> dict:
    estimated = _estimate_tokens(messages)
    budget_used = min(estimated / DEMO_CONTEXT_LIMIT, 1.0)
    return {
        "budget_used": round(budget_used, 4),
        "estimated_tokens": estimated,
        "context_limit": DEMO_CONTEXT_LIMIT,
        "compacted": compacted,
        "messages_evicted": messages_evicted,
        "strategy": "sliding_window" if compacted else "pass_through",
    }


def _maybe_compact(messages: list[Any]) -> tuple[list[Any], int]:
    estimated = _estimate_tokens(messages)
    budget_used = estimated / DEMO_CONTEXT_LIMIT
    if budget_used < DEMO_COMPACT_THRESHOLD:
        return messages, 0
    evict_count = max(1, int(len(messages) * 0.30))
    remaining = messages[evict_count:]
    return remaining, evict_count


# ── SSE event helpers ─────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _push(session: DemoSession, event: str, data: dict) -> None:
    await session.queue.put(_sse(event, data))


# ── Mock graph runner ─────────────────────────────────────────────────────────

async def _run_demo_mock(session: DemoSession) -> None:
    bundle = session.script or _SCRIPTS["vpn_flap"]
    try:
        async def node(name: str, delay: float) -> None:
            await _push(session, "node_start", {"node": name})
            await asyncio.sleep(delay)
            await _push(session, "node_done",  {"node": name})

        # ── Phase 1: intent ──────────────────────────────────────────────────
        await node("extract_intent", 0.8)

        # ── Clarification gate ───────────────────────────────────────────────
        clarification_context: str | None = None
        if bundle.needs_clarification:
            await _push(session, "node_start", {"node": "clarify"})
            await _push(session, "clarification_needed", {"question": bundle.clarification_question})
            await session.clarify_event.wait()
            await _push(session, "node_done", {"node": "clarify"})
            clarification_context = session.clarify_answer

        # ── Entities ─────────────────────────────────────────────────────────
        await node("extract_entities", 1.2)
        entities_payload: dict = {"entities": bundle.entities}
        if clarification_context:
            entities_payload["clarification_context"] = clarification_context
        await _push(session, "entities", entities_payload)

        # ── Plan (with few-shot memory retrieval) ────────────────────────────
        await _push(session, "node_start", {"node": "plan"})
        await asyncio.sleep(1.0)  # agent generating plan skeleton

        match = _find_few_shot_match(bundle)
        if match:
            match.few_shot_used = True
            await _push(session, "few_shot", {
                "history_id": match.id,
                "domain": match.domain,
                "description": match.description,
                "reason": (
                    f"Similar {match.domain} incident resolved in {match.duration_seconds}s — "
                    f"reusing {match.steps_count}-step plan as few-shot example"
                ),
            })
            await asyncio.sleep(0.8)  # agent incorporating the few-shot example
        else:
            await asyncio.sleep(0.8)

        await _push(session, "node_done", {"node": "plan"})

        # Budget: post-plan ~37% (green — no warning yet)
        await _push(session, "budget", _build_budget_event(_synthetic_msgs(5600)))

        # ── HITL review ───────────────────────────────────────────────────────
        await _push(session, "node_start", {"node": "hitl_review"})
        await _push(session, "plan_ready", {"steps": bundle.steps})
        await session.hitl_event.wait()
        await _push(session, "node_done", {"node": "hitl_review"})

        # ── Phase 2: CoT validate → execute ──────────────────────────────────
        await node("validate_cot", 1.0)
        await _push(session, "node_start", {"node": "execute_step"})

        n_steps = len(bundle.steps)
        mid_step = n_steps // 2

        for i, step in enumerate(bundle.steps):
            delay = bundle.step_delays[i] if i < len(bundle.step_delays) else 0.6
            await asyncio.sleep(delay)
            await _push(session, "step_result", {
                "step_id": step["id"],
                "tool":    step["tool"],
                "status":  "COMPLETED",
                "output":  bundle.step_outputs.get(step["id"], {}),
            })
            # Mid-execution budget: ~72% → amber WarningBanner slides in
            if i == mid_step:
                await _push(session, "budget", _build_budget_event(_synthetic_msgs(10800)))

        await _push(session, "node_done", {"node": "execute_step"})

        # Budget: pre-compaction ~90% → red WarningBanner
        await _push(session, "budget", _build_budget_event(_synthetic_msgs(13500)))
        await asyncio.sleep(1.2)  # let red state be visible before compaction

        # Budget: post-compaction → green + CompactionBanner fires
        pre_compact = _synthetic_msgs(13500)
        post_compact, evicted = _maybe_compact(pre_compact)
        await _push(session, "budget", _build_budget_event(
            post_compact, compacted=evicted > 0, messages_evicted=evicted,
        ))

        # ── Report ────────────────────────────────────────────────────────────
        await node("report", 0.9)
        await _push(session, "report", {
            "text": bundle.report,
            "metrics": {"steps_executed": len(bundle.steps)},
        })

        # ── Append to plan history ────────────────────────────────────────────
        _history_store.append(HistoryEntry(
            id=f"live-{session.session_id[:8]}",
            action=f"resolve_{bundle.script_key}",
            domain=bundle.domain,
            description=session.message[:80] or f"Demo run: {bundle.script_key}",
            outcome="COMPLETED",
            steps_count=len(bundle.steps),
            resolved_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            duration_seconds=int(time.time() - session.start_time),
        ))

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        await _push(session, "error", {"message": str(exc)})
    finally:
        await session.queue.put(None)


# ── Graph runner (real AgentCore) ─────────────────────────────────────────────

async def _run_demo(session: DemoSession) -> None:
    if not _AGENTCORE_AVAILABLE:
        await _push(session, "error", {"message": "AgentCore not installed. Set USE_MOCK_LLM=true."})
        await session.queue.put(None)
        return
    try:
        from sre_demo.registries import build_sre_registry
        from sre_demo.incidents.vpn_tunnel_flap import INCIDENT_MESSAGE
        registry = build_sre_registry()
        checkpointer = MemorySaver()
        graph = build_graph(checkpointer=checkpointer, registry=registry)
        llm_config = default_anthropic_config()
        thread_id = str(uuid.uuid4())

        config = {"configurable": {"thread_id": thread_id, "llm_config": llm_config, "registry": registry}}
        initial_input = {
            "messages": [HumanMessage(content=session.message or INCIDENT_MESSAGE)],
            "clarification_attempts": 0, "plan_revision_attempts": 0,
            "completed_steps": [], "step_results": {}, "entities": {},
            "intent": None, "plan": None, "hitl_feedback": None,
            "hitl_response": None, "cot_trace": None, "cot_response": None, "report": None,
        }

        current_node: str | None = None
        state: dict[str, Any] = {}
        interrupted = False

        async for event in graph.astream(initial_input, config=config, stream_mode="values"):
            state = event
            messages = state.get("messages", [])
            if state.get("intent") and current_node != "extract_intent":
                if current_node:
                    await _push(session, "node_done", {"node": current_node})
                current_node = "extract_intent"
                await _push(session, "node_start", {"node": current_node})
                await _push(session, "node_done", {"node": current_node})
            if state.get("entities") and current_node != "extract_entities":
                current_node = "extract_entities"
                await _push(session, "node_start", {"node": current_node})
                await _push(session, "node_done", {"node": current_node})
                entities_out: dict[str, Any] = {}
                for domain, entity in state["entities"].items():
                    entities_out[domain] = entity.model_dump(exclude_none=True) if hasattr(entity, "model_dump") else str(entity)
                await _push(session, "entities", {"entities": entities_out})
            if state.get("plan") and current_node not in ("plan", "hitl_review"):
                current_node = "plan"
                await _push(session, "node_start", {"node": current_node})
                await _push(session, "node_done", {"node": current_node})
                msgs, evicted = _maybe_compact(messages)
                await _push(session, "budget", _build_budget_event(msgs, compacted=evicted > 0, messages_evicted=evicted))
            if state.get("plan") and state["plan"].status == "PENDING_REVIEW" and current_node != "hitl_review":
                current_node = "hitl_review"
                await _push(session, "node_start", {"node": current_node})
                plan = state["plan"]
                steps_out = [{"id": s.id, "tool": s.tool_name, "dependencies": s.dependencies or [], "status": "PENDING"} for s in plan.steps]
                await _push(session, "plan_ready", {"steps": steps_out})
                interrupted = True
                break

        if not interrupted:
            if state.get("report"):
                await _push(session, "report", {"text": state["report"], "metrics": {}})
            return

        await session.hitl_event.wait()
        await _push(session, "node_done", {"node": "hitl_review"})

        resume_input = Command(resume={"hitl_response": session.hitl_response or "approved"})
        current_node = None
        seen_steps: set[str] = set()

        async for event in graph.astream(resume_input, config=config, stream_mode="values"):
            state = event
            messages = state.get("messages", [])
            if state.get("cot_trace") and current_node != "validate_cot":
                if current_node:
                    await _push(session, "node_done", {"node": current_node})
                current_node = "validate_cot"
                await _push(session, "node_start", {"node": current_node})
            if state.get("step_results"):
                if current_node not in ("execute_step", None):
                    await _push(session, "node_done", {"node": current_node})
                current_node = "execute_step"
                for step_id, result in state["step_results"].items():
                    if step_id not in seen_steps:
                        seen_steps.add(step_id)
                        await _push(session, "step_result", {
                            "step_id": step_id, "tool": step_id,
                            "status": str(getattr(result, "status", "COMPLETED")),
                            "output": getattr(result, "output", None),
                        })
            if state.get("report") and current_node != "report":
                if current_node:
                    await _push(session, "node_done", {"node": current_node})
                current_node = "report"
                await _push(session, "node_start", {"node": current_node})

        msgs, evicted = _maybe_compact(state.get("messages", []))
        await _push(session, "budget", _build_budget_event(msgs, compacted=evicted > 0, messages_evicted=evicted))
        if state.get("report"):
            await _push(session, "node_done", {"node": "report"})
            await _push(session, "report", {"text": state["report"], "metrics": {"steps_executed": len(state.get("step_results", {}))}})

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        await _push(session, "error", {"message": str(exc)})
    finally:
        await session.queue.put(None)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if USE_SYNTHETIC:
        from sre_demo.synthetic import patch_synthetic_tools
        patch_synthetic_tools()
    _seed_history()
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="SREDemo", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── REST endpoints ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class StartRequest(BaseModel):
    session_id: str
    message: str


class ApproveRequest(BaseModel):
    session_id: str
    response: str = "approved"


class ClarifyRequest(BaseModel):
    session_id: str
    answer: str


@app.post("/api/login")
async def api_login(body: LoginRequest) -> dict:
    session_id = str(uuid.uuid4())
    session = DemoSession(session_id=session_id, username=body.username)
    _sessions[session_id] = session
    return {"session_id": session_id, "username": body.username, "model": "claude-sonnet-4-6"}


@app.post("/api/start")
async def api_start(body: StartRequest) -> dict:
    session = _sessions.get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.task and not session.task.done():
        raise HTTPException(status_code=409, detail="Session already running")
    session.message = body.message
    session.script = _dispatch_script(body.message)
    session.start_time = time.time()
    runner = _run_demo_mock if USE_MOCK_LLM else _run_demo
    session.task = asyncio.create_task(runner(session))
    return {"started": True}


@app.post("/api/approve")
async def api_approve(body: ApproveRequest) -> dict:
    session = _sessions.get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.hitl_event.is_set():
        raise HTTPException(status_code=409, detail="HITL already resolved")
    session.hitl_response = body.response
    session.hitl_event.set()
    return {"resumed": True}


@app.post("/api/clarify")
async def api_clarify(body: ClarifyRequest) -> dict:
    session = _sessions.get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.clarify_event.is_set():
        raise HTTPException(status_code=409, detail="Clarification already resolved")
    session.clarify_answer = body.answer
    session.clarify_event.set()
    return {"clarified": True}


@app.get("/api/history")
async def api_history() -> list[dict]:
    return [asdict(h) for h in reversed(_history_store[-20:])]


@app.get("/api/stream")
async def api_stream(session_id: str, request: Request) -> StreamingResponse:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    chunk = await asyncio.wait_for(session.queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if chunk is None:
                    break
                yield chunk
        except asyncio.CancelledError:
            pass
        finally:
            _sessions.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ── Static file serving ───────────────────────────────────────────────────────

_DIST = Path(__file__).parent / "frontend" / "dist"

if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> Response:
        index = _DIST / "index.html"
        return Response(content=index.read_bytes(), media_type="text/html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sre_demo.web.server:app", host="0.0.0.0", port=SERVER_PORT, reload=False)
