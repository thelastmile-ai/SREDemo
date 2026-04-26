"""
Synthetic tool registry for the SREDemo UI.

Pre-canned async functions replace real AWS/Datadog/PagerDuty calls so the
demo runs with no cloud credentials.  Each function returns realistic-looking
data for the VPN tunnel flap scenario.

Usage:
    from sre_demo.synthetic import patch_synthetic_tools
    patch_synthetic_tools()   # called once at startup when USE_SYNTHETIC_DATA=true
"""

from __future__ import annotations

import asyncio
import random
import time

import agentcore.tools.registry as _fw_registry
from sre_demo.registries import TOOL_REGISTRY as _SRE_REGISTRY


# ── Synthetic implementations ──────────────────────────────────────────────────

async def aws_describe_vpn_connections(
    vpn_connection_ids: list[str] | None = None,
    region: str = "us-east-1",
) -> dict:
    await asyncio.sleep(0.6)
    return {
        "connections": [
            {
                "vpn_connection_id": "vpn-0a1b2c3d",
                "state": "available",
                "customer_gateway_id": "cgw-boston-01",
                "vpn_gateway_id": "vgw-corp-east",
                "tunnels": [
                    {
                        "outside_ip": "203.0.113.10",
                        "status": "DOWN",
                        "status_message": "Phase 2 IKE SA deleted. DPD timeout after 3 missed heartbeats.",
                        "ike_phase": "phase2",
                        "accepted_route_count": 0,
                    },
                    {
                        "outside_ip": "203.0.113.11",
                        "status": "DOWN",
                        "status_message": "Phase 2 negotiation failed. CHILD_SA rekey timeout.",
                        "ike_phase": "phase2",
                        "accepted_route_count": 0,
                    },
                ],
                "branch": "Boston",
            },
            {
                "vpn_connection_id": "vpn-0e4f5a6b",
                "state": "available",
                "customer_gateway_id": "cgw-newyork-01",
                "vpn_gateway_id": "vgw-corp-east",
                "tunnels": [
                    {
                        "outside_ip": "198.51.100.20",
                        "status": "DOWN",
                        "status_message": "Phase 2 lifetime mismatch. Peer proposed 3600s, local is 28800s.",
                        "ike_phase": "phase2",
                        "accepted_route_count": 0,
                    },
                    {
                        "outside_ip": "198.51.100.21",
                        "status": "UP",
                        "status_message": "IPSEC IS UP",
                        "ike_phase": "phase2",
                        "accepted_route_count": 4,
                    },
                ],
                "branch": "New York",
            },
            {
                "vpn_connection_id": "vpn-0c7d8e9f",
                "state": "available",
                "customer_gateway_id": "cgw-chicago-01",
                "vpn_gateway_id": "vgw-corp-east",
                "tunnels": [
                    {
                        "outside_ip": "192.0.2.30",
                        "status": "DOWN",
                        "status_message": "Phase 2 deleted after DPD timeout. 4 consecutive failures.",
                        "ike_phase": "phase2",
                        "accepted_route_count": 0,
                    },
                    {
                        "outside_ip": "192.0.2.31",
                        "status": "DOWN",
                        "status_message": "Phase 2 IKE rekey failed. Transform mismatch (AES-256 vs AES-128).",
                        "ike_phase": "phase2",
                        "accepted_route_count": 0,
                    },
                ],
                "branch": "Chicago",
            },
        ]
    }


async def aws_describe_customer_gateway(
    customer_gateway_id: str,
    region: str = "us-east-1",
) -> dict:
    await asyncio.sleep(0.4)
    gateways = {
        "cgw-boston-01":  {"ip_address": "203.0.113.1",  "bgp_asn": "65001", "state": "available", "device_type": "Cisco ASA 5505"},
        "cgw-newyork-01": {"ip_address": "198.51.100.1", "bgp_asn": "65002", "state": "available", "device_type": "Cisco ASA 5505"},
        "cgw-chicago-01": {"ip_address": "192.0.2.1",    "bgp_asn": "65003", "state": "available", "device_type": "Palo Alto PA-220"},
    }
    data = gateways.get(customer_gateway_id, {"ip_address": "0.0.0.0", "bgp_asn": "65000", "state": "unknown"})
    return {"customer_gateway_id": customer_gateway_id, **data}


async def aws_reset_vpn_tunnel(
    vpn_connection_id: str,
    outside_ip: str,
    region: str = "us-east-1",
) -> dict:
    await asyncio.sleep(1.2)
    return {
        "vpn_connection_id": vpn_connection_id,
        "outside_ip": outside_ip,
        "action": "ModifyVpnTunnelOptions",
        "status": "succeeded",
        "new_state": "UP",
        "message": f"Tunnel {outside_ip} reset. Phase 2 SA re-established with standardised lifetime 28800s.",
    }


async def aws_check_bgp_status(
    vpn_connection_id: str,
    region: str = "us-east-1",
) -> dict:
    await asyncio.sleep(0.5)
    return {
        "vpn_connection_id": vpn_connection_id,
        "bgp_status": "established",
        "asn_local": "64512",
        "asn_peer": "65001",
        "prefixes_advertised": 12,
        "prefixes_received": 4,
        "uptime_seconds": 14,
    }


async def dd_query_metrics(
    query: str,
    from_ts: int | None = None,
    to_ts: int | None = None,
    site: str = "datadoghq.com",
) -> dict:
    await asyncio.sleep(0.7)
    now = int(time.time())
    # Simulate packet-loss spike aligned with the VPN flap window
    series = []
    for i in range(12):
        ts = now - (11 - i) * 300
        if i < 8:
            val = round(random.uniform(85, 100), 1)
        else:
            val = round(random.uniform(0, 5), 1)
        series.append({"timestamp": ts, "value": val})
    return {
        "query": query,
        "series": [
            {
                "metric": "aws.vpn.tunnel_state",
                "display_name": "VPN Tunnel State",
                "pointlist": series,
                "unit": "%",
            }
        ],
        "from_date": now - 3600,
        "to_date": now,
    }


async def network_verify_connectivity(
    target: str,
    port: int = 443,
    protocol: str = "tcp",
    timeout_seconds: int = 5,
) -> dict:
    await asyncio.sleep(0.8)
    branch_targets = {"erp.boston.corp": False, "erp.newyork.corp": False, "erp.chicago.corp": False}
    reachable = branch_targets.get(target, True)
    return {
        "target": target,
        "port": port,
        "protocol": protocol,
        "reachable": reachable,
        "latency_ms": round(random.uniform(2, 8), 1) if reachable else None,
        "error": None if reachable else "Connection timed out — VPN tunnel DOWN",
    }


async def pd_create_incident(
    title: str,
    severity: str,
    body: str,
    service_id: str | None = None,
    routing_key: str | None = None,
) -> dict:
    await asyncio.sleep(0.5)
    return {
        "incident_id": f"PD-{random.randint(10000, 99999)}",
        "title": title,
        "severity": severity,
        "status": "triggered",
        "html_url": "https://acme.pagerduty.com/incidents/Q1A2B3C4D5",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


async def pd_add_incident_note(
    incident_id: str,
    content: str,
    from_email: str | None = None,
) -> dict:
    await asyncio.sleep(0.3)
    return {"incident_id": incident_id, "note_id": f"NOTE-{random.randint(100, 999)}", "status": "added"}


async def pd_update_incident_status(
    incident_id: str,
    status: str,
    resolution: str | None = None,
    from_email: str | None = None,
) -> dict:
    await asyncio.sleep(0.3)
    return {"incident_id": incident_id, "status": status, "updated": True}


# ── Registry ──────────────────────────────────────────────────────────────────

SYNTHETIC_TOOL_REGISTRY: dict = {
    "aws_describe_vpn_connections":  aws_describe_vpn_connections,
    "aws_describe_customer_gateway": aws_describe_customer_gateway,
    "aws_reset_vpn_tunnel":          aws_reset_vpn_tunnel,
    "aws_check_bgp_status":          aws_check_bgp_status,
    "dd_query_metrics":              dd_query_metrics,
    "network_verify_connectivity":   network_verify_connectivity,
    "pd_create_incident":            pd_create_incident,
    "pd_add_incident_note":          pd_add_incident_note,
    "pd_update_incident_status":     pd_update_incident_status,
}


def patch_synthetic_tools() -> None:
    """Replace real tool callables with pre-canned synthetic versions."""
    _fw_registry.TOOL_REGISTRY.update(SYNTHETIC_TOOL_REGISTRY)
    _SRE_REGISTRY.update(SYNTHETIC_TOOL_REGISTRY)
