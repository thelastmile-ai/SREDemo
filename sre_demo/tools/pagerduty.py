"""
PagerDuty incident management tools.

Uses the PagerDuty REST API v2 for incident lifecycle management.
The Events API v2 is used for incident creation (simpler, no routing key
permissions needed for read operations).

References:
  PagerDuty Events API v2 (create incident):
    https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI2Nw-send-an-event-to-pager-duty
  PagerDuty REST API — Incidents:
    https://developer.pagerduty.com/api-reference/b3A6Mjc0ODIwNg-update-an-incident
  PagerDuty REST API — Notes:
    https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI3Mg-create-a-note-on-an-incident

Environment variables required:
  PD_API_KEY       — PagerDuty REST API token (Bearer auth)
  PD_ROUTING_KEY   — Events API v2 integration key (for pd_create_incident)
  PD_FROM_EMAIL    — Email address of the PagerDuty user making changes
"""

from __future__ import annotations
import os
from typing import Any

import httpx


_PD_API_KEY      = os.getenv("PD_API_KEY", "")
_PD_ROUTING_KEY  = os.getenv("PD_ROUTING_KEY", "")
_PD_FROM_EMAIL   = os.getenv("PD_FROM_EMAIL", "sre-agent@example.com")
_PD_API_BASE     = "https://api.pagerduty.com"
_PD_EVENTS_BASE  = "https://events.pagerduty.com/v2"


def _rest_headers() -> dict[str, str]:
    return {
        "Authorization": f"Token token={_PD_API_KEY}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json",
        "From": _PD_FROM_EMAIL,
    }


async def pd_create_incident(
    title: str,
    severity: str,
    body: str,
    service_id: str,
) -> dict[str, Any]:
    """
    Create a PagerDuty incident via the Events API v2.

    Notifies the on-call engineer immediately. Must be called BEFORE any
    production change (rule-003) so every tunnel reset is traceable to an
    open incident.

    Returns incident_id used for subsequent pd_add_incident_note and
    pd_update_incident_status calls.

    API: PagerDuty Events API v2 — enqueue event
    Reference: https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI2Nw-send-an-event-to-pager-duty
    """
    # Map P1/P2/P3 to PagerDuty severity
    pd_severity = {"P1": "critical", "P2": "error", "P3": "warning"}.get(
        severity.upper(), "error"
    )

    payload = {
        "routing_key": _PD_ROUTING_KEY,
        "event_action": "trigger",
        "payload": {
            "summary": title,
            "severity": pd_severity,
            "source": service_id,
            "custom_details": {"body": body, "severity": severity},
        },
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.post(
                f"{_PD_EVENTS_BASE}/enqueue", json=payload
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            return {
                "incident_id": None,
                "status": "error",
                "assigned_to": None,
                "error": str(e),
            }

    body_json = response.json()
    return {
        "incident_id": body_json.get("dedup_key") or body_json.get("incident_key"),
        "status": body_json.get("status", "triggered"),
        "assigned_to": None,   # Events API does not return assignee; use REST API incidents endpoint if needed
        "message": body_json.get("message"),
    }


async def pd_add_incident_note(
    incident_id: str,
    note: str,
) -> dict[str, Any]:
    """
    Add a resolution note to an existing PagerDuty incident.

    Document root cause and follow-up actions BEFORE marking the incident
    resolved (rule-005). Required for post-incident review.

    API: PagerDuty REST API — POST /incidents/{id}/notes
    Reference: https://developer.pagerduty.com/api-reference/b3A6Mjc0ODI3Mg-create-a-note-on-an-incident
    """
    payload = {"note": {"content": note}}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.post(
                f"{_PD_API_BASE}/incidents/{incident_id}/notes",
                headers=_rest_headers(),
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            return {
                "note_id": None,
                "created_at": None,
                "error": str(e),
            }

    note_data = response.json().get("note", {})
    return {
        "note_id": note_data.get("id"),
        "created_at": note_data.get("created_at"),
    }


async def pd_update_incident_status(
    incident_id: str,
    status: str,
) -> dict[str, Any]:
    """
    Update a PagerDuty incident status.

    Use 'acknowledged' when investigation begins, 'resolved' when the
    incident is closed. Must only be called AFTER pd_add_incident_note
    (rule-005) — do not close an incident without a root cause note.

    API: PagerDuty REST API — PUT /incidents/{id}
    Reference: https://developer.pagerduty.com/api-reference/b3A6Mjc0ODIwNg-update-an-incident
    """
    payload = {
        "incident": {
            "type": "incident_reference",
            "status": status.lower(),
        }
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.put(
                f"{_PD_API_BASE}/incidents/{incident_id}",
                headers=_rest_headers(),
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            return {
                "incident_id": incident_id,
                "status": None,
                "resolved_at": None,
                "error": str(e),
            }

    incident = response.json().get("incident", {})
    return {
        "incident_id": incident.get("id", incident_id),
        "status": incident.get("status"),
        "resolved_at": incident.get("resolved_at"),
    }
