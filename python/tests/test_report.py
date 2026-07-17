"""Ported from src/evolveguard/report/index.test.ts."""
import json

import pytest

from evolveguard.errors import EvolveGuardError
from evolveguard.report import read_baseline, read_report, write_baseline, write_report
from evolveguard.types import (
    Baseline,
    CapabilityEntry,
    EvolveGuardReport,
    ExpectedToolCall,
    FixtureDiff,
    FixtureSnapshot,
    Summary,
)


class TestBaselineReadWrite:
    def _baseline(self):
        return Baseline(
            schema_version=1,
            skill_name="demo",
            skill_path="/skills/demo/SKILL.md",
            recorded_at="2026-07-14T00:00:00.000Z",
            full_capability_surface=[CapabilityEntry(tool="fs.read", source="declared")],
            fixtures=[
                FixtureSnapshot(
                    id="f1",
                    prompt="summarize a PR diff",
                    expected_tool_calls=[ExpectedToolCall(tool="fs.read")],
                    tool_call_sequence=[CapabilityEntry(tool="fs.read", source="declared")],
                )
            ],
        )

    def test_round_trips_baseline(self, tmp_path):
        p = str(tmp_path / ".evolveguard-baseline.json")
        baseline = self._baseline()
        write_baseline(p, baseline)
        read = read_baseline(p)
        assert read == baseline

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(EvolveGuardError):
            read_baseline(str(tmp_path / "nope.json"))

    def test_invalid_json_raises(self, tmp_path):
        p = tmp_path / "bad-baseline.json"
        p.write_text("not json")
        with pytest.raises(EvolveGuardError):
            read_baseline(str(p))

    def test_missing_required_fields_raises(self, tmp_path):
        p = tmp_path / "incomplete-baseline.json"
        p.write_text(json.dumps({"schemaVersion": 1}))
        with pytest.raises(EvolveGuardError):
            read_baseline(str(p))


class TestReportReadWrite:
    def _report(self):
        return EvolveGuardReport(
            schema_version=1,
            skill_name="demo",
            skill_path="/skills/demo/SKILL.md",
            checked_at="2026-07-15T00:00:00.000Z",
            results=[
                FixtureDiff(id="f1", prompt="summarize a PR diff", verdict="PASS", changes=[])
            ],
            surface_changes=[],
            summary=Summary(pass_count=1, drift=0, total=1),
            exit_code=0,
        )

    def test_round_trips_report(self, tmp_path):
        p = str(tmp_path / "evolveguard-report.json")
        report = self._report()
        write_report(p, report)
        read = read_report(p)
        assert read == report

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(EvolveGuardError):
            read_report(str(tmp_path / "nope.json"))

    def test_invalid_json_raises(self, tmp_path):
        p = tmp_path / "bad-report.json"
        p.write_text("not json")
        with pytest.raises(EvolveGuardError):
            read_report(str(p))
