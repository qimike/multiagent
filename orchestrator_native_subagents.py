"""
ALTERNATIVE orchestration using the Claude Agent SDK's *native* subagents.

Instead of Python driving each agent (see main_orchestrator.py), here a single
parent "orchestrator" query() is given four AgentDefinitions plus the Agent tool,
and the MODEL decides when to invoke each subagent.

Trade-offs vs. main_orchestrator.py:
  + Closer to "the agent owns the workflow"; less glue code.
  + Each subagent still runs in its own isolated context window automatically.
  - Less deterministic: routing, JSON shape, and which files get written are up
    to the model, so guaranteeing clean per-domain JSON on disk is harder.
  - Subagents cannot spawn their own subagents (one level deep).

Use main_orchestrator.py when you need reliable, validated JSON artifacts.
Use this when you want the model to own the end-to-end flow.

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    python orchestrator_native_subagents.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query

from agents import DOMAIN_AGENTS

ROOT = Path(__file__).parent


def all_tool_servers() -> dict:
    """Every domain server plus the shared server, keyed by name (deduped)."""
    servers: dict = {}
    for agent in DOMAIN_AGENTS:
        servers.update(agent.tool_servers())
    return servers


def all_tool_names() -> list[str]:
    """Every mcp__* tool name across all domains (deduped, stable order)."""
    names: list[str] = []
    for agent in DOMAIN_AGENTS:
        for name in agent.tool_names():
            if name not in names:
                names.append(name)
    return names


def build_agents() -> dict[str, AgentDefinition]:
    defs: dict[str, AgentDefinition] = {}
    for agent in DOMAIN_AGENTS:
        guidelines, examples = agent.load_context()
        defs[f"{agent.key}-agent"] = AgentDefinition(
            description=f"Assesses document sections for {agent.domain} conformance.",
            prompt=(
                f"You are the {agent.domain} Conformance Agent. Assess ONLY "
                f"{agent.domain} concerns and return a strict JSON conformance result. "
                f"Load your skills ({', '.join(agent.skills)}) with the Skill tool, and "
                f"use your tools to verify claims before judging them.\n\n"
                f"GUIDELINES:\n{guidelines}\n\nEXAMPLES:\n{examples}"
            ),
            # Skill tool + the domain's custom tools (+ Read for its own files).
            tools=["Read", "Skill", *agent.tool_names()],
            skills=agent.skills,
            model=agent.model,    # per-agent model override
        )

    defs["synthesis-agent"] = AgentDefinition(
        description="Merges all domain results into one final governance report.",
        prompt=(
            "You are the Synthesis Agent. You receive the domain agents' JSON results "
            "and merge them into a single final governance report JSON with keys: "
            "overall_status, overall_score, domain_scores, top_risks, conflicts, "
            "deduplicated_recommendations, executive_summary. Never re-assess the "
            "source document yourself."
        ),
        tools=["Read", "Write"],
        model="opus",
    )
    return defs


ORCHESTRATOR_PROMPT = """You orchestrate a document governance review.

1. Read documents/source.md.
2. For each domain (Security, Data, Resilient), delegate the review to the matching
   subagent (security-agent, data-agent, resilient-agent). Each returns a JSON
   conformance result. The subagents must NOT talk to each other.
3. Collect all three JSON results and pass them to synthesis-agent for the final report.
4. Write ONE combined report to results/source.json containing the three per-domain
   results, the synthesis output, and "source_file": "source.md".
"""


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt=ORCHESTRATOR_PROMPT,
        cwd=str(ROOT),
        # "Agent" enables subagents; "Skill" enables skill loading; the mcp__* names
        # pre-approve the custom tools the subagents call.
        allowed_tools=["Read", "Write", "Glob", "Agent", "Skill", *all_tool_names()],
        mcp_servers=all_tool_servers(),       # register every domain + shared server
        agents=build_agents(),
        setting_sources=["project"],          # discover .claude/skills
        permission_mode="acceptEdits",        # auto-accept file writes for an unattended run
    )
    async for message in query(prompt="Run the full governance review now.", options=options):
        if getattr(message, "result", None):
            print(message.result)


if __name__ == "__main__":
    asyncio.run(main())
