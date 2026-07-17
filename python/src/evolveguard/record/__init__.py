"""
Captures a golden-transcript baseline for a skill: parses the skill file,
derives its declared + inferred capability surface, and snapshots each
fixture's expected tool-call sequence against that surface. This never
invokes a live agent -- see README "How it works".

Ported from src/evolveguard/record/index.ts.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..fixtures import load_fixtures
from ..snapshot import build_fixture_snapshots, load_skill
from ..types import Baseline


def record_baseline(skill_path: str, fixtures_path: str) -> Baseline:
    skill = load_skill(skill_path)
    fixtures = load_fixtures(fixtures_path)
    fixture_snapshots = build_fixture_snapshots(skill.capability_surface, fixtures)

    return Baseline(
        schema_version=1,
        skill_name=skill.name,
        skill_path=skill.skill_path,
        recorded_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        full_capability_surface=skill.capability_surface,
        fixtures=fixture_snapshots,
    )
