"""
Parses a Claude Agent Skill file (SKILL.md) or an auto-memory file
(MEMORY.md). SKILL.md files carry YAML frontmatter declaring the skill's
name and scope; MEMORY.md files typically do not, so a file with no
frontmatter is treated as declaring an empty scope, and its capability
surface is derived entirely from static evidence found in its own body
text (see derive_capability_surface below).

Frontmatter schema this parser understands:
  ---
  name: my-skill
  description: ...
  tools: [fs.read, fs.write]     # declared tool names, optional
  network: false                  # boolean, optional (default false)
  filesystem: read-only           # "none" | "read-only" | "read-write", optional (default none)
  scope: "./workspace/**"         # glob the filesystem tools are scoped to, optional (default "./**")
  hooks: ["scripts/pre-run.sh"]   # bundled hook scripts, paths relative to the skill file, optional
  ---

This schema is a superset compatible with SkillGuard's own DeclaredScope
(network: boolean, filesystem: none|read-only|read-write) -- EvolveGuard
reuses the same field names and parsing pattern deliberately so a skill
author only has to think about one frontmatter shape across both tools.

Ported from src/evolveguard/parser/skillmd.ts.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

import yaml

from ..paths import resolve_within_base
from ..types import CapabilityEntry, DeclaredScope, EvidenceRef, ParsedSkillFile

_FRONTMATTER_RE = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---")

_KNOWN_FILESYSTEM_VALUES = {"none", "read-only", "read-write"}


def parse_skill_file(content: str, file_base_name: str) -> ParsedSkillFile:
    match = _FRONTMATTER_RE.match(content)

    def base_name() -> str:
        return os.path.splitext(os.path.basename(file_base_name))[0]

    if not match:
        return ParsedSkillFile(
            name=base_name(),
            has_frontmatter=False,
            declared_scope=DeclaredScope(
                tools=[], network=False, filesystem="none", scope="./**", hooks=[]
            ),
            body=content,
        )

    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        data = None

    record = data if isinstance(data, dict) else {}

    raw_name = record.get("name")
    name = (
        raw_name.strip()
        if isinstance(raw_name, str) and raw_name.strip()
        else base_name()
    )

    description = record.get("description")
    if not isinstance(description, str):
        description = None

    raw_tools = record.get("tools")
    tools = [t for t in raw_tools if isinstance(t, str)] if isinstance(raw_tools, list) else []

    network = record.get("network") is True

    filesystem_raw = record.get("filesystem")
    filesystem = (
        filesystem_raw
        if isinstance(filesystem_raw, str) and filesystem_raw in _KNOWN_FILESYSTEM_VALUES
        else "none"
    )

    raw_scope = record.get("scope")
    scope = raw_scope if isinstance(raw_scope, str) and raw_scope.strip() else "./**"

    raw_hooks = record.get("hooks")
    hooks = [h for h in raw_hooks if isinstance(h, str)] if isinstance(raw_hooks, list) else []

    body = content[match.end() :]

    return ParsedSkillFile(
        name=name,
        description=description,
        has_frontmatter=True,
        declared_scope=DeclaredScope(
            tools=tools, network=network, filesystem=filesystem, scope=scope, hooks=hooks
        ),
        body=body,
    )


# Note: `curl`/`wget` deliberately have no trailing `\s` baked into the
# alternation -- `\b` after "curl" already requires a non-word character to
# follow (a space, a flag like "-X", end of string, all count), so
# consuming the whitespace into the match would break that boundary check
# whenever the very next character after the space is itself non-word (e.g.
# "curl -X ..."), silently missing real command lines.
_NETWORK_EVIDENCE_RE = re.compile(
    r"\b(fetch|axios|http\.request|https\.request|requests\.(get|post|put|delete)"
    r"|urllib\.request|urlopen|socket\.socket|curl|wget)\b",
    re.IGNORECASE,
)

_FS_WRITE_EVIDENCE_RE = re.compile(
    r"""\b(fs\.writeFile|fs\.writeFileSync|fs\.appendFile|fs\.unlink|open\([^)]*['"]w"""
    r"""|os\.remove|os\.rmdir|shutil\.rmtree)\b|>\s*/|rm\s+-rf""",
    re.IGNORECASE,
)


def _first_match_line(content: str, pattern: re.Pattern) -> Optional[int]:
    m = pattern.search(content)
    if not m:
        return None
    return content.count("\n", 0, m.start()) + 1


def infer_hook_evidence(
    skill_dir: str, hooks: List[str]
) -> Dict[str, List[Dict[str, object]]]:
    """
    Reads a skill's declared hook scripts (paths validated against the
    skill's own directory -- see paths.py) and scans each for static
    evidence of network or filesystem-write behavior. This is the same
    read-only, regex-based evidence model SkillGuard uses; EvolveGuard
    never executes anything from the skill or its hooks.
    """
    network_evidence: List[Dict[str, object]] = []
    fs_write_evidence: List[Dict[str, object]] = []

    for hook_path in hooks:
        try:
            abs_path = resolve_within_base(skill_dir, hook_path)
        except Exception:
            continue

        try:
            with open(abs_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            continue

        net_line = _first_match_line(content, _NETWORK_EVIDENCE_RE)
        if net_line is not None:
            network_evidence.append({"file": hook_path, "line": net_line})

        fs_line = _first_match_line(content, _FS_WRITE_EVIDENCE_RE)
        if fs_line is not None:
            fs_write_evidence.append({"file": hook_path, "line": fs_line})

    return {"networkEvidence": network_evidence, "fsWriteEvidence": fs_write_evidence}


def derive_capability_surface(
    parsed: ParsedSkillFile, skill_dir: str
) -> List[CapabilityEntry]:
    """
    Derives the full capability surface for a parsed skill: declared entries
    from frontmatter, plus inferred entries from static evidence in the
    skill's own body text and any bundled hook scripts. This is the
    deterministic "transcript baseline" EvolveGuard records and later
    re-derives on replay -- see README "How it works" for why this is not a
    live LLM run.
    """
    entries: List[CapabilityEntry] = []
    seen = set()

    def add_declared(tool: str, scope: Optional[str] = None) -> None:
        key = f"declared:{tool}"
        if key in seen:
            return
        seen.add(key)
        entries.append(CapabilityEntry(tool=tool, source="declared", scope=scope))

    for tool in parsed.declared_scope.tools:
        add_declared(tool)

    if parsed.declared_scope.network:
        add_declared("network.fetch")

    if parsed.declared_scope.filesystem in ("read-only", "read-write"):
        add_declared("fs.read", parsed.declared_scope.scope)
    if parsed.declared_scope.filesystem == "read-write":
        add_declared("fs.write", parsed.declared_scope.scope)

    # Inferred evidence from the skill body itself (covers MEMORY.md, which has no frontmatter).
    body_net_line = _first_match_line(parsed.body, _NETWORK_EVIDENCE_RE)
    body_fs_line = _first_match_line(parsed.body, _FS_WRITE_EVIDENCE_RE)

    inferred_network_evidence: List[Dict[str, object]] = (
        [{"file": "(body)", "line": body_net_line}] if body_net_line is not None else []
    )
    inferred_fs_evidence: List[Dict[str, object]] = (
        [{"file": "(body)", "line": body_fs_line}] if body_fs_line is not None else []
    )

    # Inferred evidence from bundled hook scripts declared in frontmatter.
    hook_evidence = infer_hook_evidence(skill_dir, parsed.declared_scope.hooks)
    inferred_network_evidence.extend(hook_evidence["networkEvidence"])
    inferred_fs_evidence.extend(hook_evidence["fsWriteEvidence"])

    def add_inferred(tool: str, evidence: List[Dict[str, object]]) -> None:
        if not evidence:
            return
        key = f"inferred:{tool}"
        if key in seen:
            existing = next(
                (e for e in entries if e.source == "inferred" and e.tool == tool), None
            )
            if existing is not None:
                existing.evidence = (existing.evidence or []) + [
                    EvidenceRef(file=str(e["file"]), line=int(e["line"])) for e in evidence
                ]
            return
        # If this tool is already declared, do not duplicate it as a separate inferred entry --
        # declared coverage takes precedence and the inferred evidence is redundant confirmation.
        if f"declared:{tool}" in seen:
            return
        seen.add(key)
        entries.append(
            CapabilityEntry(
                tool=tool,
                source="inferred",
                evidence=[
                    EvidenceRef(file=str(e["file"]), line=int(e["line"])) for e in evidence
                ],
            )
        )

    add_inferred("network.fetch", inferred_network_evidence)
    add_inferred("fs.write", inferred_fs_evidence)

    return entries
