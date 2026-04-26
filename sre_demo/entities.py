"""
NetworkIncidentEntity — entity schema for the networking domain.

Fields are all optional: the LLM fills only what is present in the user's text.
Missing IDs (vpn_connection_ids, customer_gateway_id) are discovered by the
first tool calls (aws_describe_vpn_connections with vpn_connection_ids=None).

Schema reference: AWS Site-to-Site VPN concepts
  https://docs.aws.amazon.com/vpn/latest/s2svpn/VPC_VPN.html
"""

from __future__ import annotations
from agentcore.schemas.entity import EntityBase


class NetworkIncidentEntity(EntityBase):
    """Entity schema for network incidents in the networking domain."""

    # Class attribute read by InMemoryRegistryProvider.get_domain_hints()
    domain_description: str = (
        "network incidents, VPN tunnel flaps, IKE/IPsec failures, BGP outages, "
        "connectivity failures, packet loss"
    )

    # Incident metadata
    incident_id: str | None = None
    severity: str | None = None          # P1 | P2 | P3
    incident_type: str | None = None     # vpn_tunnel_flap | bgp_outage | ddos

    # AWS VPN topology
    # Discovered via aws_describe_vpn_connections(vpn_connection_ids=None) if absent
    vpn_gateway: str | None = None
    vpn_connection_ids: list[str] | None = None
    customer_gateway_id: str | None = None

    # IKE / IPsec diagnosis
    # Phase 1 vs Phase 2 distinction comes from VgwTelemetry.StatusMessage in the API response.
    # Reference: https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html
    ike_phase: str | None = None         # phase1 | phase2 | both
    ike_failure_reason: str | None = None

    # Incident scope
    affected_branches: list[str] | None = None
    affected_services: list[str] | None = None
    customer_facing: bool | None = None
