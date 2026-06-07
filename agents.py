"""Per-domain agent configuration and prompt construction.

Each domain agent runs in its OWN isolated query() call (a fresh session), so
agents never share memory or talk to each other. The orchestrator is the only
component that sees all of their outputs. This mirrors the architecture rule:

    Orchestrator -> Sub-Agent
    Sub-Agent    -> Orchestrator
    Orchestrator -> Synthesis Agent
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import shared_tools
from schema import OUTPUT_SCHEMA_EXAMPLE, STATUS_VALUES

AGENTS_DIR = Path(__file__).parent / "agents"


# A regular module `agents.py` and a package-like directory `agents/` coexist in
# this repo, so `from agents.security import tools` can't resolve (the module name
# `agents` wins). Load each domain's tools.py directly from its file path instead.
_TOOLS_CACHE: dict[str, ModuleType] = {}


def _load_domain_tools(key: str) -> ModuleType:
    if key not in _TOOLS_CACHE:
        path = AGENTS_DIR / key / "tools.py"
        spec = importlib.util.spec_from_file_location(f"agents_{key}_tools", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load tools for domain {key!r} at {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _TOOLS_CACHE[key] = module
    return _TOOLS_CACHE[key]


@dataclass
class DomainAgent:
    domain: str                 # e.g. "Security"
    key: str                    # e.g. "security" (folder + filename stem)
    model: str                  # "sonnet" | "opus" | "haiku" (per-agent override)
    skills: list[str] = field(default_factory=list)  # e.g. ["conformance-common", "security-review"]

    @property
    def guidelines_path(self) -> Path:
        return AGENTS_DIR / self.key / "guidelines.md"

    @property
    def examples_path(self) -> Path:
        return AGENTS_DIR / self.key / "examples.md"

    def load_context(self) -> tuple[str, str]:
        return _safe_read(self.guidelines_path), _safe_read(self.examples_path)

    def tool_servers(self) -> dict[str, Any]:
        """MCP server config for this domain plus the shared server, keyed by name.

        Suitable for ClaudeAgentOptions(mcp_servers=...).
        """
        mod = _load_domain_tools(self.key)
        return {
            mod.SERVER_NAME: mod.MCP_SERVER,
            shared_tools.SERVER_NAME: shared_tools.MCP_SERVER,
        }

    def tool_names(self) -> list[str]:
        """Fully-qualified `mcp__<server>__<tool>` names for allowed_tools."""
        mod = _load_domain_tools(self.key)
        return [*mod.TOOL_NAMES, *shared_tools.TOOL_NAMES]


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # A missing guidelines/examples file means the agent runs UNGROUNDED
        # (assessing against the model's general knowledge instead of the
        # domain rules). Warn loudly so this can't happen silently.
        print(
            f"  WARNING: context file not found: {path.relative_to(Path(__file__).parent)} "
            "-- agent will run WITHOUT these guidelines",
            file=sys.stderr,
        )
        return "(none provided)"


# Registry. Routing is now tag-based (see route_sections in main_orchestrator.py):
# each `## [Tag]` section is owned by exactly one of these domains. No keyword lists.
DOMAIN_AGENTS: list[DomainAgent] = [
    DomainAgent(
        "Security", "security", "opus",
        skills=["conformance-common", "security-review"],
    ),
    DomainAgent(
        "Data", "data", "opus",
        skills=["conformance-common", "data-review"],
    ),
    DomainAgent(
        "Resilient", "resilient", "opus",
        skills=["conformance-common", "resilient-review"],
    ),
]

DOMAIN_BY_KEY = {a.key: a for a in DOMAIN_AGENTS}
DOMAIN_BY_NAME = {a.domain: a for a in DOMAIN_AGENTS}

SYNTHESIS_MODEL = "opus"

_SCHEMA_BLOCK = json.dumps(OUTPUT_SCHEMA_EXAMPLE, indent=2)


def build_domain_system_prompt(agent: DomainAgent, guidelines: str, examples: str) -> str:
    skills_line = (
        ", ".join(agent.skills) if agent.skills else "(none)"
    )
    tool_names = agent.tool_names()
    tools_line = ", ".join(tool_names) if tool_names else "(none)"
    return f"""You are the {agent.domain} Conformance Agent in a document governance pipeline.

Your ONLY job is to assess the provided document section(s) against the {agent.domain}
guidelines below, then return a single conformance result as STRICT JSON.

You do NOT have access to any other domain's guidelines, and you must NOT comment on
other domains. Assess ONLY {agent.domain} concerns.

===== SKILLS =====
Load these skills with the Skill tool for the procedure and the full guideline set:
{skills_line}

===== TOOLS =====
You may call these tools to verify claims before judging them (call -> read result
-> reason). Do not invent results; if a tool says "unknown", record that:
{tools_line}
When you are done verifying, return the JSON object as your final message.

===== {agent.domain.upper()} GUIDELINES =====
{guidelines}

===== {agent.domain.upper()} FEW-SHOT EXAMPLES =====
{examples}

===== OUTPUT CONTRACT =====
Return ONE JSON object and NOTHING else. No markdown fences, no commentary.
It must match this exact shape:

{_SCHEMA_BLOCK}

Rules:
- "domain" must be exactly "{agent.domain}".
- "status" must be one of {list(STATUS_VALUES)}.
- "conformance_score" is an integer 0-100 for how well the section meets the guidelines.
- "confidence" is a float 0.0-1.0 for how sure you are given the available text.
- "evidence" lists concrete supporting quotes from the section, each mapped to a guideline.
- "violations" lists unmet guidelines, each with a short reason.
- "recommendations" are concrete, actionable fixes.
- "exceptions" lists anything you could not assess (missing info, ambiguous text).
- If the section has no {agent.domain} content at all, use status "NOT_APPLICABLE",
  score 0, and explain in "exceptions"."""


def build_domain_user_prompt(section_text: str) -> str:
    return (
        "Assess the following document section(s) and return the JSON result.\n\n"
        "===== SECTION(S) TO REVIEW =====\n"
        f"{section_text}\n"
    )


def build_synthesis_system_prompt() -> str:
    return """You are the Synthesis Agent in a document governance pipeline.

You receive the JSON conformance results from each domain agent (Security, Data,
Resilient) plus any conflicts the orchestrator detected. You NEVER re-assess the
source document yourself — you only merge and summarize what the domain agents found.
Do not call any tools — respond with the JSON object directly.

Produce ONE JSON object and NOTHING else (no markdown fences), matching this shape:

{
  "overall_status": "PARTIALLY_COMPLIANT",
  "overall_score": 0,
  "domain_scores": { "Security": 0, "Data": 0, "Resilient": 0 },
  "top_risks": [
    { "domain": "Security", "risk": "...", "severity": "HIGH" }
  ],
  "conflicts": [],
  "deduplicated_recommendations": [ "..." ],
  "executive_summary": "2-4 sentence plain-language summary for leadership."
}

Rules:
- "overall_score" is a sensible weighted roll-up of the domain scores.
- "severity" is one of "HIGH", "MEDIUM", "LOW".
- Deduplicate recommendations that say the same thing across domains.
- "top_risks" surfaces the most serious violations first.
- Echo or interpret the conflicts passed to you in "conflicts".
- Be concise and factual; do not invent findings that aren't in the inputs."""
