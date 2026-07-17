"""
Loads a skill file from disk and builds per-fixture tool-call sequence
snapshots against its capability surface. Ported from src/evolveguard/snapshot.ts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import List

from .errors import EvolveGuardError
from .parser.skillmd import derive_capability_surface, parse_skill_file
from .types import CapabilityEntry, ExpectedToolCall, Fixture, FixtureSnapshot


@dataclass
class LoadedSkill:
    name: str
    skill_path: str
    skill_dir: str
    capability_surface: List[CapabilityEntry]


def load_skill(skill_path: str) -> LoadedSkill:
    """Reads a skill file from disk, parses it, and derives its full capability surface."""
    try:
        with open(skill_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError as err:
        raise EvolveGuardError(
            f'Could not read skill file at "{skill_path}".',
            str(err),
            "Pass a valid path to a SKILL.md or MEMORY.md file.",
        ) from err

    skill_dir = os.path.dirname(os.path.abspath(skill_path))
    parsed = parse_skill_file(content, skill_path)
    capability_surface = derive_capability_surface(parsed, skill_dir)

    return LoadedSkill(
        name=parsed.name,
        skill_path=os.path.abspath(skill_path),
        skill_dir=skill_dir,
        capability_surface=capability_surface,
    )


def _scope_glob_match(text: str, pattern: str) -> bool:
    """
    A minimal, first-party glob matcher used only to compare two declared
    filesystem scopes (e.g. "./workspace/**" vs "./**") for compatibility --
    it is never run against the filesystem. `fnmatch` treats `*` as matching
    any character including path separators, which mirrors this project's
    only actual use case (checking whether one scope glob subsumes another),
    without pulling in a third-party glob-matching dependency.
    """
    return fnmatch(text, pattern)


def build_fixture_snapshots(
    surface: List[CapabilityEntry], fixtures: List[Fixture]
) -> List[FixtureSnapshot]:
    """
    Builds the per-fixture tool-call sequence snapshot for a given capability
    surface. A fixture with no expected_tool_calls is treated as exercising
    the skill's entire surface (a broad smoke-test fixture); a fixture that
    declares specific expected tool calls only snapshots the surface entries
    matching those tools (and, if scope_matches is given, only entries whose
    declared/inferred scope satisfies that glob).
    """
    snapshots: List[FixtureSnapshot] = []

    for fixture in fixtures:
        expected = fixture.expected_tool_calls or []

        if not expected:
            snapshots.append(
                FixtureSnapshot(
                    id=fixture.id,
                    prompt=fixture.prompt,
                    expected_tool_calls=[],
                    tool_call_sequence=surface,
                )
            )
            continue

        def matches(entry: CapabilityEntry) -> bool:
            for exp in expected:
                if exp.tool != entry.tool:
                    continue
                if not exp.scope_matches:
                    return True
                if not entry.scope:
                    continue
                if _scope_glob_match(entry.scope, exp.scope_matches) or _scope_glob_match(
                    exp.scope_matches, entry.scope
                ):
                    return True
            return False

        tool_call_sequence = [entry for entry in surface if matches(entry)]

        snapshots.append(
            FixtureSnapshot(
                id=fixture.id,
                prompt=fixture.prompt,
                expected_tool_calls=expected,
                tool_call_sequence=tool_call_sequence,
            )
        )

    return snapshots
