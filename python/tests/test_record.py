"""Ported from src/evolveguard/record/index.test.ts."""
import json
from datetime import datetime

from evolveguard.record import record_baseline


def test_records_baseline_with_per_fixture_tool_call_sequences(tmp_path):
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(
        '---\nname: demo\nfilesystem: read-only\nscope: "./workspace/**"\n---\nbody'
    )

    fixtures_path = tmp_path / "fixtures.json"
    fixtures_path.write_text(
        json.dumps(
            [
                {
                    "id": "read-fixture",
                    "prompt": "summarize a PR diff",
                    "expectedToolCalls": [{"tool": "fs.read"}],
                }
            ]
        )
    )

    baseline = record_baseline(str(skill_path), str(fixtures_path))

    assert baseline.skill_name == "demo"
    assert len(baseline.fixtures) == 1
    assert [e.tool for e in baseline.fixtures[0].tool_call_sequence] == ["fs.read"]
    assert "fs.read" in [e.tool for e in baseline.full_capability_surface]
    # recorded_at must be a valid ISO-8601 timestamp
    datetime.fromisoformat(baseline.recorded_at.replace("Z", "+00:00"))
