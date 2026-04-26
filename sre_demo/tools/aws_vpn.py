"""
AWS Site-to-Site VPN tools.

All tools run boto3 (synchronous) in a thread-pool executor so they are
compatible with the async LangGraph execution engine.

AWS API references:
  DescribeVpnConnections:
    https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeVpnConnections.html
  DescribeCustomerGateways:
    https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeCustomerGateways.html
  ModifyVpnTunnelOptions (used for tunnel renegotiation):
    https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyVpnTunnelOptions.html

VgwTelemetry field notes:
  - Status is "UP" or "DOWN" only — no explicit Phase1/Phase2 field.
  - StatusMessage contains IKE phase detail, e.g.
      "IKE phase 1 SA established"
      "IKE phase 2 SA timeout - deleting IPSEC SA"
  - AcceptedRouteCount > 0 is used as a BGP-established proxy since BGP
    session state is not exposed in the EC2 API.
    Reference: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_VgwTelemetry.html
"""

from __future__ import annotations
import asyncio
from functools import partial
from typing import Any

import boto3
from botocore.exceptions import ClientError


def _get_ec2(region: str):
    return boto3.client("ec2", region_name=region)


async def _run(fn, *args, **kwargs):
    """Run a synchronous boto3 call in the default thread-pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))


async def aws_describe_vpn_connections(
    vpn_connection_ids: list[str] | None,
    region: str = "us-east-1",
) -> dict[str, Any]:
    """
    Query AWS EC2 for VPN tunnel state.

    Pass vpn_connection_ids=None to list ALL VPN connections in the region —
    the standard first step when connection IDs are not yet known.

    VgwTelemetry.Status is UP or DOWN.
    VgwTelemetry.StatusMessage indicates IKE phase detail.
    VgwTelemetry.AcceptedRouteCount reflects BGP route reception.

    API: ec2.describe_vpn_connections()
    Reference: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeVpnConnections.html
    """
    ec2 = _get_ec2(region)

    kwargs: dict[str, Any] = {}
    if vpn_connection_ids:
        kwargs["VpnConnectionIds"] = vpn_connection_ids
    else:
        # Exclude deleted/deleting connections when listing all
        kwargs["Filters"] = [{"Name": "state", "Values": ["available", "pending"]}]

    try:
        response = await _run(ec2.describe_vpn_connections, **kwargs)
    except ClientError as e:
        return {"error": str(e), "connections": []}

    connections = []
    for conn in response.get("VpnConnections", []):
        tunnels = []
        for t in conn.get("VgwTelemetry", []):
            # Infer IKE phase from StatusMessage since Phase1/Phase2 are not
            # separate API fields.
            msg = t.get("StatusMessage", "")
            if "phase 1" in msg.lower():
                ike_phase = "phase1"
            elif "phase 2" in msg.lower() or "ipsec" in msg.lower():
                ike_phase = "phase2"
            else:
                ike_phase = "unknown"

            tunnels.append({
                "outside_ip": t.get("OutsideIpAddress"),
                "status": t.get("Status"),           # "UP" | "DOWN"
                "status_message": msg,
                "ike_phase": ike_phase,
                "accepted_route_count": t.get("AcceptedRouteCount", 0),
                "last_status_change": str(t.get("LastStatusChange", "")),
            })

        tags = {tag["Key"]: tag["Value"] for tag in conn.get("Tags", [])}
        connections.append({
            "vpn_connection_id": conn["VpnConnectionId"],
            "state": conn.get("State"),
            "customer_gateway_id": conn.get("CustomerGatewayId"),
            "vpn_gateway_id": conn.get("VpnGatewayId") or conn.get("TransitGatewayId"),
            "tunnels": tunnels,
            "name": tags.get("Name", ""),
        })

    return {"connections": connections, "region": region}


async def aws_describe_customer_gateway(
    customer_gateway_id: str,
    region: str = "us-east-1",
) -> dict[str, Any]:
    """
    Fetch customer gateway configuration from AWS.

    Returns BGP ASN, outside IP, certificate validity, and routing type.
    Use this to detect config drift (wrong BGP ASN, expired certificate)
    BEFORE attempting a tunnel reset — a config mismatch will cause the
    reset to fail immediately.

    API: ec2.describe_customer_gateways()
    Reference: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeCustomerGateways.html
    """
    ec2 = _get_ec2(region)

    try:
        response = await _run(
            ec2.describe_customer_gateways,
            CustomerGatewayIds=[customer_gateway_id],
        )
    except ClientError as e:
        return {"error": str(e), "customer_gateway": None}

    gateways = response.get("CustomerGateways", [])
    if not gateways:
        return {"error": f"Customer gateway {customer_gateway_id} not found", "customer_gateway": None}

    cgw = gateways[0]
    tags = {tag["Key"]: tag["Value"] for tag in cgw.get("Tags", [])}

    return {
        "customer_gateway": {
            "customer_gateway_id": cgw["CustomerGatewayId"],
            "state": cgw.get("State"),
            "type": cgw.get("Type"),            # "ipsec.1"
            "ip_address": cgw.get("IpAddress"),
            "bgp_asn": cgw.get("BgpAsn"),
            "certificate_arn": cgw.get("CertificateArn"),  # None if pre-shared key
            "routing_type": "bgp" if cgw.get("BgpAsn") else "static",
            "name": tags.get("Name", ""),
        }
    }


async def aws_reset_vpn_tunnel(
    vpn_connection_id: str,
    outside_ip: str,
    region: str = "us-east-1",
) -> dict[str, Any]:
    """
    Force IKE Phase 2 SA renegotiation for a flapping VPN tunnel.

    There is no standalone ResetVpnTunnel API. The correct mechanism is
    modify_vpn_tunnel_options with StartupAction='start' and
    DPDTimeoutAction='restart', which forces the VGW to initiate a new
    IKE exchange immediately.

    Safe to call on individual tunnels — each tunnel is independent.
    Run in parallel for multiple tunnels on the same VPN connection.

    API: ec2.modify_vpn_tunnel_options()
    Reference: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyVpnTunnelOptions.html
    """
    ec2 = _get_ec2(region)

    try:
        response = await _run(
            ec2.modify_vpn_tunnel_options,
            VpnConnectionId=vpn_connection_id,
            VpnTunnelOutsideIpAddress=outside_ip,
            TunnelOptions={
                "StartupAction": "start",        # VGW initiates IKE immediately
                "DPDTimeoutAction": "restart",   # restart SA on DPD timeout (not clear/none)
                "DPDTimeoutSeconds": 30,
            },
        )
    except ClientError as e:
        return {
            "vpn_connection_id": vpn_connection_id,
            "outside_ip": outside_ip,
            "success": False,
            "error": str(e),
        }

    conn = response.get("VpnConnection", {})
    return {
        "vpn_connection_id": vpn_connection_id,
        "outside_ip": outside_ip,
        "success": True,
        "new_state": conn.get("State"),
        "phase2_renegotiating": True,
        "message": (
            "Tunnel options updated with StartupAction=start. "
            "VGW will initiate IKE Phase 2 renegotiation."
        ),
    }


async def aws_check_bgp_status(
    vpn_connection_id: str,
    region: str = "us-east-1",
) -> dict[str, Any]:
    """
    Check BGP peering state for a VPN connection after tunnel reset.

    BGP session state (Established/Idle) is not exposed in the EC2 API.
    AcceptedRouteCount > 0 is used as the BGP-established proxy: routes
    are only received via BGP when the session is in Established state.

    Reference: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_VgwTelemetry.html
    Background: https://docs.aws.amazon.com/vpn/latest/s2svpn/Troubleshooting.html
    """
    ec2 = _get_ec2(region)

    try:
        response = await _run(
            ec2.describe_vpn_connections,
            VpnConnectionIds=[vpn_connection_id],
        )
    except ClientError as e:
        return {"error": str(e), "vpn_connection_id": vpn_connection_id}

    connections = response.get("VpnConnections", [])
    if not connections:
        return {"error": f"{vpn_connection_id} not found", "vpn_connection_id": vpn_connection_id}

    tunnels = []
    for t in connections[0].get("VgwTelemetry", []):
        accepted = t.get("AcceptedRouteCount", 0)
        # BGP proxy: routes received ↔ BGP session Established
        bgp_state = "Established" if (t.get("Status") == "UP" and accepted > 0) else "Idle"
        tunnels.append({
            "outside_ip": t.get("OutsideIpAddress"),
            "tunnel_status": t.get("Status"),
            "bgp_state": bgp_state,
            "prefixes_received": accepted,
            "prefixes_advertised": None,    # not available via EC2 API
        })

    all_established = all(t["bgp_state"] == "Established" for t in tunnels)
    return {
        "vpn_connection_id": vpn_connection_id,
        "bgp_state": "Established" if all_established else "Idle",
        "tunnels": tunnels,
        "note": (
            "bgp_state is derived from AcceptedRouteCount > 0 — "
            "BGP session state is not directly exposed in the EC2 API."
        ),
    }
