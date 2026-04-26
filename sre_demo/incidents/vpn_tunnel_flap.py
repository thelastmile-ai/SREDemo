"""
VPN tunnel flap incident — the message the SRE types into the agent.

This is a plain natural language description. The SRE does not know (and
should not need to know) AWS VPN connection IDs, customer gateway IDs, or
IKE error codes. The agent discovers those through its first tool calls.

What extract_entities will pull from this text:
  incident_type     = "vpn_tunnel_flap"     ← "VPN tunnels... keep dropping"
  ike_phase         = "phase2"              ← "Phase 2 keeps renegotiating"
  affected_branches = ["Boston","New York","Chicago"]
  affected_services = ["ERP", "VoIP"]
  customer_facing   = True                  ← "450 users affected"
  severity          = "P2"                  ← inferred from 450 users + services

Fields that will be null (discovered by first tool calls):
  vpn_connection_ids  ← aws_describe_vpn_connections(vpn_connection_ids=None)
  customer_gateway_id ← from describe_vpn_connections response
  vpn_gateway         ← from describe_vpn_connections response
  ike_failure_reason  ← from VgwTelemetry.StatusMessage
"""

INCIDENT_MESSAGE = """\
Our VPN tunnels to the Boston, New York and Chicago branch offices keep dropping.
Phase 2 keeps renegotiating. ERP and VoIP are degraded, about 450 users affected.
"""
