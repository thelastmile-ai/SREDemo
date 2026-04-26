"""
Network operations tool — end-to-end connectivity verification.

Performs an ICMP ping and TCP port check from the agent host toward the
branch-office subnet gateway. Used AFTER tunnel reset (rule-004) to confirm
traffic is actually flowing before closing the PagerDuty incident.

Note: ICMP ping requires the agent to be running on the VPN gateway host or
a host within the VPC with a route to the branch subnet. The TCP check is a
fallback for environments where ICMP is filtered.
"""

from __future__ import annotations
import asyncio
import socket
import time
from typing import Any


async def network_verify_connectivity(
    source: str,
    target: str,
    port: int = 443,
) -> dict[str, Any]:
    """
    Run end-to-end connectivity test toward a branch office subnet gateway.

    Performs:
      1. ICMP ping via asyncio subprocess (requires ping binary)
      2. TCP socket connect to target:port as a fallback / additional check

    source: source hostname or IP (informational — subprocess ping uses OS routing)
    target: target hostname or IP (branch office subnet gateway or reachability probe host)
    port:   TCP port to verify (default 443)

    Returns latency and packet loss from the ping result.
    """
    results: dict[str, Any] = {
        "source": source,
        "target": target,
        "port": port,
    }

    # ── ICMP ping ─────────────────────────────────────────────────────────────
    ping_start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "4", "-W", "2", target,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        ping_elapsed = time.monotonic() - ping_start
        output = stdout.decode(errors="replace")

        # Parse "4 packets transmitted, 4 received, 0% packet loss"
        packet_loss_pct = 100.0
        latency_ms = None
        for line in output.splitlines():
            if "packet loss" in line:
                for token in line.split(","):
                    if "packet loss" in token:
                        try:
                            packet_loss_pct = float(token.strip().split("%")[0])
                        except ValueError:
                            pass
            if "rtt min/avg/max" in line or "round-trip" in line:
                # "rtt min/avg/max/mdev = 1.234/2.345/3.456/0.5 ms"
                try:
                    stats = line.split("=")[1].strip().split("/")
                    latency_ms = round(float(stats[1]), 2)  # avg
                except (IndexError, ValueError):
                    pass

        results["icmp_reachable"] = proc.returncode == 0
        results["packet_loss_pct"] = packet_loss_pct
        results["latency_ms"] = latency_ms
        results["ping_elapsed_secs"] = round(ping_elapsed, 2)

    except asyncio.TimeoutError:
        results["icmp_reachable"] = False
        results["packet_loss_pct"] = 100.0
        results["latency_ms"] = None
        results["ping_error"] = "ping timed out"
    except FileNotFoundError:
        results["icmp_reachable"] = None
        results["ping_error"] = "ping binary not found"

    # ── TCP port check ────────────────────────────────────────────────────────
    tcp_start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(target, port),
            timeout=5,
        )
        writer.close()
        await writer.wait_closed()
        results["tcp_reachable"] = True
        results["tcp_latency_ms"] = round((time.monotonic() - tcp_start) * 1000, 2)
    except (asyncio.TimeoutError, OSError) as e:
        results["tcp_reachable"] = False
        results["tcp_error"] = str(e)

    # ── Overall reachability ──────────────────────────────────────────────────
    results["reachable"] = results.get("icmp_reachable") or results.get("tcp_reachable", False)
    return results
