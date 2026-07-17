"""Ported from src/evolveguard/replay/index.test.ts."""
import json

from evolveguard.record import record_baseline
from evolveguard.replay import replay_skill


def _setup(tmp_path):
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("---\nname: demo\nfilesystem: read-only\n---\nbody")
    fixtures_path = tmp_path / "fixtures.json"
    fixtures_path.write_text(
        json.dumps([{"id": "f1", "prompt": "read a file", "expectedToolCalls": [{"tool": "fs.read"}]}])
    )
    return str(skill_path), str(fixtures_path)


def test_reproduces_same_sequence_when_skill_unchanged(tmp_path):
    skill_path, fixtures_path = _setup(tmp_path)
    baseline = record_baseline(skill_path, fixtures_path)
    replay = replay_skill(skill_path, baseline)
    assert [e.tool for e in replay.fixtures[0].tool_call_sequence] == [
        e.tool for e in baseline.fixtures[0].tool_call_sequence
    ]


def test_picks_up_new_capability_after_skill_edited(tmp_path):
    skill_path, fixtures_path = _setup(tmp_path)
    baseline = record_baseline(skill_path, fixtures_path)

    with open(skill_path, "w") as fh:
        fh.write("---\nname: demo\nfilesystem: read-write\n---\nbody")

    # The baseline fixture only expected fs.read, so re-snapshotting against
    # the edited (now read-write) surface still yields fs.read for this
    # fixture -- fs.write only shows up in fixtures that expect it, or in
    # full_capability_surface, which is exactly what diff/ is responsible
    # for comparing at the whole-surface level.
    replay = replay_skill(skill_path, baseline)
    assert "fs.write" in [e.tool for e in replay.full_capability_surface]
