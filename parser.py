"""Deterministic Markdown section parser and section-ownership router.

This is the ONLY place section ownership is decided. Claude agents never discover
their own sections or determine ownership — the parser assigns every section to a
domain (or to None for context-only sections), and the orchestrator hands each agent
the sections it owns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from domains import DOMAIN_CONFIG, DOMAINS  # single source of truth

# Deterministic heading -> domain rules, generated from DOMAIN_CONFIG. Matched
# case-insensitively against the section heading; first matching rule wins; unmatched
# sections are context-only (domain=None).
_HEADING_RULES: list[tuple[str, str]] = [
    (cfg["routing"], key) for key, cfg in DOMAIN_CONFIG.items()
]

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass
class Section:
    heading: str
    level: int
    domain: str | None       # owning domain, decided here (deterministic)
    line_start: int          # 1-based line of the heading
    line_end: int            # 1-based last line of the section body
    body: str                # full section text including the heading line

    @property
    def line_range(self) -> str:
        return f"{self.line_start}-{self.line_end}"


def _route_heading(heading: str) -> str | None:
    text = heading.lower()
    for pattern, domain in _HEADING_RULES:
        if re.search(pattern, text):
            return domain
    return None


def parse_sections(markdown: str) -> list[Section]:
    """Split Markdown into sections by ATX headings, with 1-based line ranges and a
    deterministically assigned owning domain."""
    lines = markdown.splitlines()
    # Find heading positions.
    heads: list[tuple[int, int, str]] = []  # (index0, level, heading_text)
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    sections: list[Section] = []
    # Preamble before the first heading (context-only).
    first = heads[0][0] if heads else len(lines)
    if first > 0 and "".join(lines[:first]).strip():
        body = "\n".join(lines[:first]).strip()
        sections.append(
            Section("(preamble)", 0, None, 1, first, body)
        )

    for idx, (start, level, heading) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        sections.append(
            Section(
                heading=heading,
                level=level,
                domain=_route_heading(heading),
                line_start=start + 1,
                line_end=end,
                body=body,
            )
        )
    return sections


def routing_map(sections: list[Section]) -> dict[str, str]:
    """{heading: domain} for every section that was assigned an owning domain."""
    return {s.heading: s.domain for s in sections if s.domain}


def sections_by_domain(sections: list[Section]) -> dict[str, list[Section]]:
    """{domain: [sections it owns]} for the four domains (domains with none omitted)."""
    out: dict[str, list[Section]] = {}
    for s in sections:
        if s.domain:
            out.setdefault(s.domain, []).append(s)
    return out
