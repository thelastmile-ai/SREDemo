"""
Datadog metrics tool for VPN tunnel health monitoring.

Uses the Datadog Metrics API v2 to query time-series data.

References:
  Datadog AWS VPN Integration:
    https://docs.datadoghq.com/integrations/amazon_vpn/
  Datadog Metrics Query API v2:
    https://docs.datadoghq.com/api/latest/metrics/#query-timeseries-data
  Key metrics:
    aws.vpn.tunnel_state       — 1=UP, 0=DOWN (per tunnel)
    aws.vpn.packets_received   — inbound packet count
    aws.vpn.packets_sent       — outbound packet count
    aws.vpn.packet_loss_count  — dropped packets

Environment variables required:
  DD_API_KEY  — Datadog API key
  DD_APP_KEY  — Datadog application key
  DD_SITE     — Datadog site (default: datadoghq.com)
"""

from __future__ import annotations
import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import httpx


_DD_API_KEY = os.getenv("DD_API_KEY", "")
_DD_APP_KEY = os.getenv("DD_APP_KEY", "")
_DD_SITE    = os.getenv("DD_SITE", "datadoghq.com")


async def dd_query_metrics(
    metric: str,
    host: str,
    minutes: int = 30,
) -> dict[str, Any]:
    """
    Query Datadog metrics API for VPN tunnel health data.

    Recommended metrics:
      aws.vpn.tunnel_state      — 1=UP, 0=DOWN (flap visible as oscillation)
      aws.vpn.packets_received  — confirms traffic flow after tunnel reset
      aws.vpn.packet_loss_count — quantifies degradation before reset

    The host filter maps to the VPN gateway hostname or AWS resource tag.

    API: Datadog Metrics Query API v2
    Reference: https://docs.datadoghq.com/api/latest/metrics/#query-timeseries-data
    """
    now = int(datetime.now(timezone.utc).timestamp())
    frm = now - (minutes * 60)
    query = f"{metric}{{host:{host}}}"

    url = f"https://api.{_DD_SITE}/api/v1/query"
    headers = {
        "DD-API-KEY": _DD_API_KEY,
        "DD-APPLICATION-KEY": _DD_APP_KEY,
        "Content-Type": "application/json",
    }
    params = {"from": frm, "to": now, "query": query}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
        except httpx.HTTPError as e:
            return {
                "metric": metric,
                "host": host,
                "minutes": minutes,
                "error": str(e),
                "data_points": [],
            }

    body = response.json()
    series = body.get("series", [])
    data_points = []
    if series:
        for ts, val in series[0].get("pointlist", []):
            data_points.append({
                "timestamp": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat(),
                "value": val,
            })

    return {
        "metric": metric,
        "host": host,
        "minutes": minutes,
        "data_points": data_points,
        "point_count": len(data_points),
        "query": query,
    }
