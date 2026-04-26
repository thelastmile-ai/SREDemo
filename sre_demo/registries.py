"""
SRE Demo registry setup.

Builds the InMemoryRegistryProvider with:
  - Schema registry: NetworkIncidentEntity → "networking" domain
  - Tool contracts: 9 tools with real AWS/Datadog/PagerDuty signatures
  - Playbook: 6 hard rules + 2 soft rules derived from AWS VPN troubleshooting guide

References used to derive playbook rules:
  AWS Site-to-Site VPN Troubleshooting Guide:
    https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html
  AWS VPN Telemetry fields (VgwTelemetry):
    https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_VgwTelemetry.html
  Datadog AWS VPN Integration metrics:
    https://docs.datadoghq.com/integrations/amazon_vpn/
"""

from __future__ import annotations
from agentcore.registry.base import ToolContract, PlaybookRule, Playbook
from agentcore.registry.inmemory import InMemoryRegistryProvider

from sre_demo.entities import NetworkIncidentEntity
from sre_demo.tools.aws_vpn import (
    aws_describe_vpn_connections,
    aws_describe_customer_gateway,
    aws_reset_vpn_tunnel,
    aws_check_bgp_status,
)
from sre_demo.tools.datadog import dd_query_metrics
from sre_demo.tools.network_ops import network_verify_connectivity
from sre_demo.tools.pagerduty import (
    pd_create_incident,
    pd_add_incident_note,
    pd_update_incident_status,
)

# ── Schema registry ────────────────────────────────────────────────────────────

SCHEMA_REGISTRY = {
    "networking": NetworkIncidentEntity,
}

# ── Tool registry (callable map for execute_step) ─────────────────────────────

TOOL_REGISTRY = {
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

# ── Tool contracts (LLM prompt context) ───────────────────────────────────────

_TOOL_CONTRACTS = [
    ToolContract(
        name="aws_describe_vpn_connections",
        domain="networking",
        description=(
            "Query AWS EC2 for VPN tunnel state via describe_vpn_connections(). "
            "Pass vpn_connection_ids=None to list ALL connections in the region — "
            "use this when IDs are not yet known. "
            "VgwTelemetry.Status is UP or DOWN. "
            "VgwTelemetry.StatusMessage indicates IKE phase (phase1/phase2). "
            "Returns outside_ip per tunnel — required for aws_reset_vpn_tunnel."
        ),
        input_schema={
            "vpn_connection_ids": "list[str] | None",
            "region": "str",
        },
        output_description=(
            "dict: {connections: [{vpn_connection_id, state, customer_gateway_id, "
            "tunnels: [{outside_ip, status, status_message, ike_phase, accepted_route_count}]}]}"
        ),
        version="v1.0",
        owner="sre-team",
    ),

    ToolContract(
        name="aws_describe_customer_gateway",
        domain="networking",
        description=(
            "Fetch customer gateway configuration from AWS via describe_customer_gateways(). "
            "Returns BGP ASN, outside IP, certificate ARN, and routing type. "
            "Use BEFORE reset to detect config drift — a BGP ASN mismatch or expired "
            "certificate will cause the tunnel reset to fail immediately. "
            "Reference: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeCustomerGateways.html"
        ),
        input_schema={
            "customer_gateway_id": "str",
            "region": "str",
        },
        output_description=(
            "dict: {customer_gateway: {customer_gateway_id, state, ip_address, bgp_asn, "
            "certificate_arn, routing_type}}"
        ),
        version="v1.0",
        owner="sre-team",
    ),

    ToolContract(
        name="aws_reset_vpn_tunnel",
        domain="networking",
        description=(
            "Force IKE Phase 2 SA renegotiation via modify_vpn_tunnel_options() with "
            "StartupAction='start' and DPDTimeoutAction='restart'. "
            "There is no standalone reset API — this is the correct mechanism. "
            "Requires outside_ip from aws_describe_vpn_connections output. "
            "Safe to call in parallel on multiple tunnels — each tunnel is independent. "
            "Reference: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyVpnTunnelOptions.html"
        ),
        input_schema={
            "vpn_connection_id": "str",
            "outside_ip": "str",
            "region": "str",
        },
        output_description=(
            "dict: {vpn_connection_id, outside_ip, success, new_state, phase2_renegotiating, message}"
        ),
        version="v1.0",
        owner="sre-team",
    ),

    ToolContract(
        name="aws_check_bgp_status",
        domain="networking",
        description=(
            "Check BGP peering state after tunnel reset. "
            "BGP session state is not directly available in the EC2 API — "
            "AcceptedRouteCount > 0 is used as the BGP-Established proxy "
            "(routes are only received when BGP is in Established state). "
            "Run AFTER network_verify_connectivity, BEFORE closing the incident. "
            "Reference: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_VgwTelemetry.html"
        ),
        input_schema={
            "vpn_connection_id": "str",
            "region": "str",
        },
        output_description=(
            "dict: {vpn_connection_id, bgp_state, "
            "tunnels: [{outside_ip, tunnel_status, bgp_state, prefixes_received}]}"
        ),
        version="v1.0",
        owner="sre-team",
    ),

    ToolContract(
        name="dd_query_metrics",
        domain="networking",
        description=(
            "Query Datadog metrics API for VPN tunnel health time-series. "
            "Key metrics: aws.vpn.tunnel_state (1=UP, 0=DOWN), "
            "aws.vpn.packets_received, aws.vpn.packet_loss_count. "
            "Use to quantify packet loss before reset and confirm recovery after. "
            "Reference: https://docs.datadoghq.com/integrations/amazon_vpn/"
        ),
        input_schema={
            "metric": "str",
            "host": "str",
            "minutes": "int",
        },
        output_description=(
            "dict: {metric, host, data_points: [{timestamp, value}], point_count}"
        ),
        version="v1.0",
        owner="sre-team",
    ),

    ToolContract(
        name="network_verify_connectivity",
        domain="networking",
        description=(
            "Run end-to-end connectivity test from agent host toward branch office subnet. "
            "ICMP ping + TCP socket check. "
            "Must run AFTER tunnel reset — a tunnel can show Phase2=UP in AWS but "
            "BGP Idle means no traffic flows. This is the traffic-plane verification. "
        ),
        input_schema={
            "source": "str",
            "target": "str",
            "port": "int",
        },
        output_description=(
            "dict: {reachable, icmp_reachable, packet_loss_pct, latency_ms, "
            "tcp_reachable, tcp_latency_ms}"
        ),
        version="v1.0",
        owner="sre-team",
    ),

    ToolContract(
        name="pd_create_incident",
        domain="networking",
        description=(
            "Create a PagerDuty incident via Events API v2. "
            "MUST be called BEFORE any production change (rule-003) — "
            "every tunnel reset must be traceable to an open incident. "
            "Returns incident_id used by pd_add_incident_note and pd_update_incident_status. "
            "Reference: https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI2Nw-send-an-event-to-pager-duty"
        ),
        input_schema={
            "title": "str",
            "severity": "str",
            "body": "str",
            "service_id": "str",
        },
        output_description="dict: {incident_id, status, assigned_to}",
        version="v1.0",
        owner="sre-team",
    ),

    ToolContract(
        name="pd_add_incident_note",
        domain="networking",
        description=(
            "Add a resolution note to an existing PagerDuty incident. "
            "Document root cause and follow-up actions BEFORE marking resolved (rule-005). "
            "Reference: https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI3Mg-create-a-note-on-an-incident"
        ),
        input_schema={
            "incident_id": "str",
            "note": "str",
        },
        output_description="dict: {note_id, created_at}",
        version="v1.0",
        owner="sre-team",
    ),

    ToolContract(
        name="pd_update_incident_status",
        domain="networking",
        description=(
            "Update a PagerDuty incident status to 'acknowledged' or 'resolved'. "
            "Must only be called AFTER pd_add_incident_note (rule-005). "
            "Reference: https://developer.pagerduty.com/api-reference/b3A6Mjc0ODIwNg-update-an-incident"
        ),
        input_schema={
            "incident_id": "str",
            "status": "str",
        },
        output_description="dict: {incident_id, status, resolved_at}",
        version="v1.0",
        owner="sre-team",
    ),
]

# ── Playbook ───────────────────────────────────────────────────────────────────
# Rules derived from:
#   AWS VPN Troubleshooting: https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html
#   AWS VgwTelemetry: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_VgwTelemetry.html

_NETWORKING_PLAYBOOK = Playbook(
    domain="networking",
    version="v1.0",
    owner="sre-team",
    rules=[
        PlaybookRule(
            id="rule-001",
            description=(
                "Always gather VPN tunnel status and metrics BEFORE attempting any reset. "
                "aws_describe_vpn_connections returns the current Phase1/Phase2 state via "
                "StatusMessage and the outside_ip required for the reset call. "
                "dd_query_metrics quantifies packet loss to confirm impact. "
                "Source: AWS VPN Troubleshooting Guide — check IKE SA before IPsec SA."
            ),
            before=["aws_describe_vpn_connections", "dd_query_metrics"],
            after=["aws_reset_vpn_tunnel"],
            severity="hard",
        ),

        PlaybookRule(
            id="rule-002",
            description=(
                "Check customer gateway configuration BEFORE resetting tunnels. "
                "A BGP ASN mismatch, incorrect outside IP, or expired certificate will cause "
                "the tunnel reset to fail immediately — there is no point resetting until "
                "the config is confirmed correct. "
                "Source: AWS VPN Troubleshooting Guide — config mismatch is the primary root cause."
            ),
            before=["aws_describe_customer_gateway"],
            after=["aws_reset_vpn_tunnel"],
            severity="hard",
        ),

        PlaybookRule(
            id="rule-003",
            description=(
                "Create a PagerDuty incident BEFORE making any production changes. "
                "Every tunnel reset must be traceable to an open incident for audit and "
                "post-incident review. The incident_id is also required by subsequent "
                "pd_add_incident_note and pd_update_incident_status calls."
            ),
            before=["pd_create_incident"],
            after=["aws_reset_vpn_tunnel"],
            severity="hard",
        ),

        PlaybookRule(
            id="rule-004",
            description=(
                "Verify end-to-end connectivity AND BGP peering AFTER tunnel reset, "
                "BEFORE closing the incident. "
                "A tunnel can show Phase2=UP in AWS (VgwTelemetry.Status=UP) but still not "
                "pass traffic if BGP is not in Established state (AcceptedRouteCount=0). "
                "Both network_verify_connectivity (traffic plane) and aws_check_bgp_status "
                "(control plane) must pass. "
                "Source: AWS VPN Troubleshooting Guide — verify BGP after tunnel restoration."
            ),
            before=["aws_reset_vpn_tunnel"],
            after=["network_verify_connectivity", "aws_check_bgp_status"],
            severity="hard",
        ),

        PlaybookRule(
            id="rule-005",
            description=(
                "Add resolution notes with root cause BEFORE marking the incident resolved. "
                "Required for post-incident review. The note must include: what was done, "
                "the root cause, and recommended follow-up actions (e.g. align IKE lifetime settings)."
            ),
            before=["pd_add_incident_note"],
            after=["pd_update_incident_status"],
            severity="hard",
        ),

        PlaybookRule(
            id="rule-006",
            description=(
                "Verify IKE Phase 1 is UP before diagnosing or resetting Phase 2. "
                "aws_describe_vpn_connections returns both Phase 1 and Phase 2 state via "
                "VgwTelemetry.StatusMessage. If Phase 1 is DOWN, the root cause is a config "
                "mismatch or routing issue — a Phase 2 reset will not fix it. "
                "Source: AWS VPN Troubleshooting Guide — IKE SA must be established before IPsec SA."
            ),
            before=["aws_describe_vpn_connections"],
            after=["aws_reset_vpn_tunnel"],
            severity="hard",
        ),

        PlaybookRule(
            id="rule-007",
            description=(
                "Initial data gathering steps — aws_describe_vpn_connections, "
                "aws_describe_customer_gateway, and dd_query_metrics — can all run in parallel. "
                "They are independent read operations with no shared state."
            ),
            tools=["aws_describe_vpn_connections", "aws_describe_customer_gateway", "dd_query_metrics"],
            pattern="parallel_allowed",
            severity="soft",
        ),

        PlaybookRule(
            id="rule-008",
            description=(
                "Multiple tunnel resets can run in parallel. "
                "Each VPN tunnel is independent — resetting Boston does not affect New York or Chicago. "
                "Run aws_reset_vpn_tunnel once per vpn_connection_id with its outside_ip."
            ),
            tools=["aws_reset_vpn_tunnel"],
            pattern="parallel_allowed",
            severity="soft",
        ),
    ],
)

# ── Factory ────────────────────────────────────────────────────────────────────

def build_sre_registry() -> InMemoryRegistryProvider:
    """
    Build and return the InMemoryRegistryProvider for the SRE demo.
    Pass the returned registry to build_graph() as the registry argument.
    """
    return InMemoryRegistryProvider(
        schema_map=SCHEMA_REGISTRY,
        tool_map=TOOL_REGISTRY,
        tool_contracts=_TOOL_CONTRACTS,
        playbooks={"networking": _NETWORKING_PLAYBOOK},
    )
