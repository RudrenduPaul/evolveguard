"""
Compares baseline vs. replayed tool-call sequences and classifies the
result. PASS = identical tool set and scopes. DRIFT = a tool appeared that
wasn't there before, a tool disappeared, or a tool's scope changed -- each
surfaced as a specific, cited change, not an unexplained failure.

Ported from src/evolveguard/diff/index.ts.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..types import (
    Baseline,
    CapabilityChange,
    CapabilityEntry,
    EvolveGuardReport,
    FixtureDiff,
    FixtureSnapshot,
    ReplayResult,
    Summary,
)


def diff_fixture(
    baseline_fixture: FixtureSnapshot, replayed_fixture: FixtureSnapshot
) -> FixtureDiff:
    changes: List[CapabilityChange] = []

    baseline_by_tool: Dict[str, CapabilityEntry] = {
        e.tool: e for e in baseline_fixture.tool_call_sequence
    }
    replayed_by_tool: Dict[str, CapabilityEntry] = {
        e.tool: e for e in replayed_fixture.tool_call_sequence
    }

    for tool, entry in replayed_by_tool.items():
        if tool not in baseline_by_tool:
            changes.append(
                CapabilityChange(
                    kind="added",
                    tool=tool,
                    new_scope=entry.scope,
                    message=(
                        f"new tool call: {tool} (baseline had none) -- this edit "
                        "introduces a capability the baseline never used"
                    ),
                )
            )

    for tool, entry in baseline_by_tool.items():
        if tool not in replayed_by_tool:
            changes.append(
                CapabilityChange(
                    kind="removed",
                    tool=tool,
                    baseline_scope=entry.scope,
                    message=(
                        f"tool call removed: {tool} (baseline required this) -- this "
                        "edit dropped a capability the baseline relied on"
                    ),
                )
            )

    for tool, baseline_entry in baseline_by_tool.items():
        replayed_entry = replayed_by_tool.get(tool)
        if replayed_entry is None:
            continue
        if (
            baseline_entry.scope
            and replayed_entry.scope
            and baseline_entry.scope != replayed_entry.scope
        ):
            changes.append(
                CapabilityChange(
                    kind="scope-changed",
                    tool=tool,
                    baseline_scope=baseline_entry.scope,
                    new_scope=replayed_entry.scope,
                    message=(
                        f'scope changed for {tool}: baseline "{baseline_entry.scope}" '
                        f'-> now "{replayed_entry.scope}"'
                    ),
                )
            )

    return FixtureDiff(
        id=baseline_fixture.id,
        prompt=baseline_fixture.prompt,
        verdict="PASS" if not changes else "DRIFT",
        changes=changes,
    )


def diff_surface(
    baseline_surface: List[CapabilityEntry], replay_surface: List[CapabilityEntry]
) -> List[CapabilityChange]:
    """
    Diffs the skill's full capability surface (declared + inferred, across
    the whole skill file) independent of any fixture. This is what catches a
    new capability that no fixture's expected_tool_calls anticipated -- a
    per-fixture diff alone can only ever compare the tools that fixture
    declared it cares about.
    """
    changes: List[CapabilityChange] = []

    baseline_by_tool: Dict[str, CapabilityEntry] = {e.tool: e for e in baseline_surface}
    replayed_by_tool: Dict[str, CapabilityEntry] = {e.tool: e for e in replay_surface}

    for tool, entry in replayed_by_tool.items():
        if tool not in baseline_by_tool:
            changes.append(
                CapabilityChange(
                    kind="added",
                    tool=tool,
                    new_scope=entry.scope,
                    message=(
                        f"new capability on the skill surface: {tool} (baseline had "
                        "none) -- no fixture's expectedToolCalls covers this tool, so "
                        "it would otherwise go unnoticed"
                    ),
                )
            )

    for tool, entry in baseline_by_tool.items():
        if tool not in replayed_by_tool:
            changes.append(
                CapabilityChange(
                    kind="removed",
                    tool=tool,
                    baseline_scope=entry.scope,
                    message=(
                        f"capability removed from the skill surface: {tool} (baseline "
                        "required this) -- this edit dropped a capability the "
                        "baseline relied on"
                    ),
                )
            )

    return changes


def diff_all(
    baseline: Baseline, replay: ReplayResult, allow_drift: bool = False
) -> EvolveGuardReport:
    """Diffs every fixture in a baseline against its replayed counterpart and builds the full report."""
    replayed_by_id = {f.id: f for f in replay.fixtures}

    results: List[FixtureDiff] = []
    for baseline_fixture in baseline.fixtures:
        replayed_fixture = replayed_by_id.get(baseline_fixture.id)
        if replayed_fixture is None:
            results.append(
                FixtureDiff(
                    id=baseline_fixture.id,
                    prompt=baseline_fixture.prompt,
                    verdict="DRIFT",
                    changes=[
                        CapabilityChange(
                            kind="removed",
                            tool="(fixture missing)",
                            message=(
                                f'fixture "{baseline_fixture.id}" is missing from the '
                                "replay -- the baseline is stale or corrupted"
                            ),
                        )
                    ],
                )
            )
            continue
        results.append(diff_fixture(baseline_fixture, replayed_fixture))

    # A capability change already surfaced through a per-fixture diff (above)
    # is not repeated here -- surface_changes exists specifically to catch a
    # change no fixture's expected_tool_calls covers, so entries for tools
    # any fixture already flagged are filtered out to avoid reporting the
    # same change twice.
    tools_covered_by_fixtures = {c.tool for r in results for c in r.changes}
    surface_changes = [
        c
        for c in diff_surface(baseline.full_capability_surface, replay.full_capability_surface)
        if c.tool not in tools_covered_by_fixtures
    ]

    pass_count = sum(1 for r in results if r.verdict == "PASS")
    drift = sum(1 for r in results if r.verdict == "DRIFT")

    any_drift = drift > 0 or len(surface_changes) > 0
    exit_code = 1 if (any_drift and not allow_drift) else 0

    return EvolveGuardReport(
        schema_version=1,
        skill_name=replay.skill_name,
        skill_path=replay.skill_path,
        checked_at=replay.replayed_at,
        results=results,
        surface_changes=surface_changes,
        summary=Summary(pass_count=pass_count, drift=drift, total=len(results)),
        exit_code=exit_code,
    )
