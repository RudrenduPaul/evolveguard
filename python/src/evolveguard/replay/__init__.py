"""
Re-parses the (possibly edited) skill file and re-derives its capability
surface using the exact same deterministic logic `record` used, then
re-snapshots each fixture from the baseline against the new surface. The
fixture list is taken from the baseline itself (not re-read from an
external fixtures.json) so `evolveguard check` only needs the skill path.

Ported from src/evolveguard/replay/index.ts.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..snapshot import build_fixture_snapshots, load_skill
from ..types import Baseline, Fixture, ReplayResult


def replay_skill(skill_path: str, baseline: Baseline) -> ReplayResult:
    skill = load_skill(skill_path)

    fixtures = [
        Fixture(id=f.id, prompt=f.prompt, expected_tool_calls=f.expected_tool_calls)
        for f in baseline.fixtures
    ]

    fixture_snapshots = build_fixture_snapshots(skill.capability_surface, fixtures)

    return ReplayResult(
        schema_version=1,
        skill_name=skill.name,
        skill_path=skill.skill_path,
        replayed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        full_capability_surface=skill.capability_surface,
        fixtures=fixture_snapshots,
    )
