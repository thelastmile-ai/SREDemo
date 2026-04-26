"""
SRE Demo — VPN Tunnel Flap

End-to-end demonstration of the AgentCore framework handling a real
AWS Site-to-Site VPN incident.

What this demo shows:
  1. extract_intent  — classifies user text as domain="networking"
  2. extract_entities — extracts typed fields from plain English; IDs are null
  3. plan            — LLM builds a DAG grounded by tool contracts + playbook
  4. hitl_review     — SRE approves or revises the plan (terminal input)
  5. validate_cot    — Opus model verifies the reasoning chain
  6. execute_step    — DAG executed; first call discovers VPN IDs from AWS
  7. report          — Final summary with root cause

Tools used (real API calls):
  AWS EC2:     describe_vpn_connections, describe_customer_gateways,
               modify_vpn_tunnel_options, (bgp via describe_vpn_connections)
  Datadog:     metrics query API v2
  PagerDuty:   Events API v2 + REST API
  stdlib:      ping + TCP socket (connectivity check)

Required environment variables:
  ANTHROPIC_API_KEY   — Claude API key
  AWS_ACCESS_KEY_ID   — AWS credentials (or use IAM role)
  AWS_SECRET_ACCESS_KEY
  AWS_DEFAULT_REGION  — default us-east-1
  DD_API_KEY          — Datadog API key
  DD_APP_KEY          — Datadog application key
  PD_API_KEY          — PagerDuty REST API token
  PD_ROUTING_KEY      — PagerDuty Events API v2 integration key
  PD_FROM_EMAIL       — PagerDuty user email for API calls
  PD_SERVICE_ID       — PagerDuty service ID for incident creation
"""

from __future__ import annotations
import asyncio
import sys
import os
import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command

# ── Path setup ────────────────────────────────────────────────────────────────
# Add AgentCore to the Python path so we can import agentcore.
# In production use, agentcore would be installed as a package.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCALABLE_AGENTS = os.path.normpath(os.path.join(_HERE, "..", "..", "AgentCore"))
if _SCALABLE_AGENTS not in sys.path:
    sys.path.insert(0, _SCALABLE_AGENTS)

# ── Framework imports ─────────────────────────────────────────────────────────
from agentcore.graph.builder import build_graph
from agentcore.llm.config import default_anthropic_config
import agentcore.tools.registry as _fw_tool_registry

# ── SRE demo imports ──────────────────────────────────────────────────────────
from sre_demo.registries import build_sre_registry, TOOL_REGISTRY
from sre_demo.incidents.vpn_tunnel_flap import INCIDENT_MESSAGE


def _patch_tool_registry() -> None:
    """
    Register SRE demo tools into the framework's global TOOL_REGISTRY.

    execute_step looks up tools by name from agentcore.tools.registry.TOOL_REGISTRY.
    The SRE tools are not in the framework package, so we inject them here
    before running the graph.
    """
    _fw_tool_registry.TOOL_REGISTRY.update(TOOL_REGISTRY)


def _print_banner() -> None:
    print("\n" + "=" * 70)
    print("  SRE Demo — VPN Tunnel Flap")
    print("  AgentCore framework end-to-end demonstration")
    print("=" * 70)


def _print_section(title: str) -> None:
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print("─" * 70)


def _print_state(state: dict[str, Any]) -> None:
    """Pretty-print relevant state fields after each node."""
    if state.get("intent"):
        intent = state["intent"]
        print(f"  Intent:  action={intent.action}  domain={intent.domain}")

    if state.get("entities"):
        print("  Entities:")
        for domain, entity in state["entities"].items():
            if hasattr(entity, "model_dump"):
                for k, v in entity.model_dump(exclude_none=True).items():
                    print(f"    {k}: {v}")
            else:
                print(f"    {domain}: {entity}")

    if state.get("plan"):
        plan = state["plan"]
        print(f"  Plan ({len(plan.steps)} steps, status={plan.status}):")
        for step in plan.steps:
            deps = f"  deps={step.dependencies}" if step.dependencies else ""
            print(f"    [{step.id}] {step.tool_name}{deps}")

    if state.get("report"):
        print(f"\n  REPORT:\n{state['report']}")


async def run_demo() -> None:
    _print_banner()

    # Register SRE tools into the framework's global tool registry
    _patch_tool_registry()

    # Build registry with SRE schema + tool contracts + VPN playbook
    registry = build_sre_registry()

    # Build graph (in-memory checkpointer for demo — no Postgres needed)
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer, registry=registry)

    # LLM config (reads ANTHROPIC_API_KEY from env)
    llm_config = default_anthropic_config()

    # Thread ID ties together all turns for this session
    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id,
            "llm_config": llm_config,
            "registry": registry,
        }
    }

    # ── Initial user message ──────────────────────────────────────────────────
    _print_section("User Query")
    print(f"\n{INCIDENT_MESSAGE.strip()}\n")

    initial_input = {
        "messages": [HumanMessage(content=INCIDENT_MESSAGE)],
        "clarification_attempts": 0,
        "plan_revision_attempts": 0,
        "completed_steps": [],
        "step_results": {},
        "entities": {},
        "intent": None,
        "plan": None,
        "hitl_feedback": None,
        "hitl_response": None,
        "cot_trace": None,
        "cot_response": None,
        "report": None,
    }

    # ── Stream graph until first interrupt ────────────────────────────────────
    print("\nRunning extract_intent → extract_entities → plan ...")

    state: dict[str, Any] = {}
    interrupted = False

    async for event in graph.astream(initial_input, config=config, stream_mode="values"):
        state = event
        # Detect HITL interrupt
        if state.get("plan") and state["plan"].status == "PENDING_REVIEW":
            interrupted = True
            break

    if not interrupted:
        # Graph finished without needing HITL (shouldn't happen in normal flow)
        _print_section("Final State")
        _print_state(state)
        return

    # ── HITL gate ─────────────────────────────────────────────────────────────
    _print_section("Plan — Awaiting SRE Approval")
    _print_state(state)

    print("\nOptions: [approved] to proceed, or type feedback to revise the plan")
    try:
        hitl_response = input("SRE> ").strip()
    except (EOFError, KeyboardInterrupt):
        hitl_response = "approved"
        print(f"(auto-approved: {hitl_response})")

    if not hitl_response:
        hitl_response = "approved"

    # Resume graph with HITL response
    resume_input = Command(resume={"hitl_response": hitl_response})

    print("\nRunning validate_cot → execute_step → report ...")

    async for event in graph.astream(resume_input, config=config, stream_mode="values"):
        state = event
        # Print step results as they arrive
        if state.get("step_results"):
            for step_id, result in state["step_results"].items():
                status = getattr(result, "status", "?")
                output = getattr(result, "output", None)
                short = str(output)[:80] + "..." if output and len(str(output)) > 80 else str(output)
                print(f"  step {step_id}: {status}  → {short}")

    # ── Final report ──────────────────────────────────────────────────────────
    _print_section("Incident Report")
    _print_state(state)

    print("\n" + "=" * 70)
    print("  Demo complete.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
