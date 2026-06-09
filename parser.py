"""Deterministic Markdown section splitter.

This file no longer decides section ownership. Section-to-domain assignment is done
semantically by the Claude native section-assignment agent — there is NO heading regex,
routing map, or `if "security" in heading` logic anywhere in Python.

What remains is purely structural: split Markdown into sections with 1-based line ranges.
This is used only as a helper by the optional `find_evidence` locator (to map a quote back
to a line number); it never assigns a domain to a section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from domains import DOMAINS  # re-exported for tools.py (guideline domain validation)

__all__ = ["Section", "parse_sections", "DOMAINS"]

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass
class Section:
    heading: str
    level: int
    line_start: int          # 1-based line of the heading
    line_end: int            # 1-based last line of the section body
    body: str                # full section text including the heading line

    @property
    def line_range(self) -> str:
        return f"{self.line_start}-{self.line_end}"


def parse_sections(markdown: str) -> list[Section]:
    """Split Markdown into sections by ATX headings, with 1-based line ranges.

    Structural only — no domain is assigned. The section-assignment agent owns the
    semantic decision of which domain(s) each section belongs to.
    """
    lines = markdown.splitlines()
    # Find heading positions.
    heads: list[tuple[int, int, str]] = []  # (index0, level, heading_text)
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    sections: list[Section] = []
    # Preamble before the first heading.
    first = heads[0][0] if heads else len(lines)
    if first > 0 and "".join(lines[:first]).strip():
        body = "\n".join(lines[:first]).strip()
        sections.append(Section("(preamble)", 0, 1, first, body))

    for idx, (start, level, heading) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        sections.append(
            Section(
                heading=heading,
                level=level,
                line_start=start + 1,
                line_end=end,
                body=body,
            )
        )
    return sections
