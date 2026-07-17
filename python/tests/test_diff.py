"""Ported from src/evolveguard/diff/index.test.ts."""
from evolveguard.diff import diff_all, diff_fixture, diff_surface
from evolveguard.types import Baseline, CapabilityEntry, ExpectedToolCall, FixtureSnapshot, ReplayResult


def _fixture(id_, prompt, tools):
    return FixtureSnapshot(
        id=id_,
        prompt=prompt,
        expected_tool_calls=[ExpectedToolCall(tool=t["tool"]) for t in tools],
        tool_call_sequence=[
            CapabilityEntry(tool=t["tool"], source="declared", scope=t.get("scope")) for t in tools
        ],
    )


class TestDiffFixture:
    def test_pass_when_unchanged(self):
        baseline = _fixture("f1", "summarize a PR diff", [{"tool": "fs.read"}])
        replayed = _fixture("f1", "summarize a PR diff", [{"tool": "fs.read"}])
        result = diff_fixture(baseline, replayed)
        assert result.verdict == "PASS"
        assert result.changes == []

    def test_drift_when_new_tool_call_appears(self):
        baseline = _fixture("f2", "scan a monorepo", [{"tool": "fs.read"}])
        replayed = _fixture("f2", "scan a monorepo", [{"tool": "fs.read"}, {"tool": "fs.write"}])
        result = diff_fixture(baseline, replayed)
        assert result.verdict == "DRIFT"
        assert len(result.changes) == 1
        assert result.changes[0].kind == "added"
        assert result.changes[0].tool == "fs.write"
        assert "new tool call: fs.write" in result.changes[0].message

    def test_drift_when_tool_call_disappears(self):
        baseline = _fixture("f3", "flag a secrets leak", [{"tool": "fs.read"}, {"tool": "fs.write"}])
        replayed = _fixture("f3", "flag a secrets leak", [{"tool": "fs.read"}])
        result = diff_fixture(baseline, replayed)
        assert result.verdict == "DRIFT"
        assert result.changes[0].kind == "removed"

    def test_drift_when_scope_changes(self):
        baseline = _fixture("f4", "write to workspace", [{"tool": "fs.write", "scope": "./workspace/**"}])
        replayed = _fixture("f4", "write to workspace", [{"tool": "fs.write", "scope": "./**"}])
        result = diff_fixture(baseline, replayed)
        assert result.verdict == "DRIFT"
        assert result.changes[0].kind == "scope-changed"
        assert "./workspace/**" in result.changes[0].message
        assert "./**" in result.changes[0].message


class TestDiffSurface:
    def test_no_changes_for_identical_surface(self):
        surface = [CapabilityEntry(tool="fs.read", source="declared")]
        assert diff_surface(surface, surface) == []

    def test_flags_capability_only_in_replay(self):
        baseline = [CapabilityEntry(tool="fs.read", source="declared")]
        replay = [
            CapabilityEntry(tool="fs.read", source="declared"),
            CapabilityEntry(tool="exec.shell", source="inferred"),
        ]
        changes = diff_surface(baseline, replay)
        assert len(changes) == 1
        assert changes[0].kind == "added"
        assert changes[0].tool == "exec.shell"


def _make_baseline():
    return Baseline(
        schema_version=1,
        skill_name="demo",
        skill_path="/skills/demo/SKILL.md",
        recorded_at="2026-07-14T00:00:00.000Z",
        full_capability_surface=[CapabilityEntry(tool="fs.read", source="declared")],
        fixtures=[_fixture("f1", "summarize a PR diff", [{"tool": "fs.read"}])],
    )


class TestDiffAll:
    def test_all_pass_exit_0(self):
        baseline = _make_baseline()
        replay = ReplayResult(
            schema_version=1,
            skill_name="demo",
            skill_path="/skills/demo/SKILL.md",
            replayed_at="2026-07-15T00:00:00.000Z",
            full_capability_surface=[CapabilityEntry(tool="fs.read", source="declared")],
            fixtures=[_fixture("f1", "summarize a PR diff", [{"tool": "fs.read"}])],
        )
        report = diff_all(baseline, replay)
        assert report.summary.pass_count == 1
        assert report.summary.drift == 0
        assert report.summary.total == 1
        assert report.exit_code == 0

    def test_drift_and_exit_1_on_new_tool_call(self):
        baseline = _make_baseline()
        replay = ReplayResult(
            schema_version=1,
            skill_name="demo",
            skill_path="/skills/demo/SKILL.md",
            replayed_at="2026-07-15T00:00:00.000Z",
            full_capability_surface=[
                CapabilityEntry(tool="fs.read", source="declared"),
                CapabilityEntry(tool="fs.write", source="declared"),
            ],
            fixtures=[
                _fixture("f1", "summarize a PR diff", [{"tool": "fs.read"}, {"tool": "fs.write"}])
            ],
        )
        report = diff_all(baseline, replay)
        assert report.summary.pass_count == 0
        assert report.summary.drift == 1
        assert report.exit_code == 1

    def test_allow_drift_stays_exit_0(self):
        baseline = _make_baseline()
        replay = ReplayResult(
            schema_version=1,
            skill_name="demo",
            skill_path="/skills/demo/SKILL.md",
            replayed_at="2026-07-15T00:00:00.000Z",
            full_capability_surface=[
                CapabilityEntry(tool="fs.read", source="declared"),
                CapabilityEntry(tool="fs.write", source="declared"),
            ],
            fixtures=[
                _fixture("f1", "summarize a PR diff", [{"tool": "fs.read"}, {"tool": "fs.write"}])
            ],
        )
        report = diff_all(baseline, replay, allow_drift=True)
        assert report.summary.drift == 1
        assert report.exit_code == 0

    def test_surface_level_change_no_fixture_expected(self):
        baseline = _make_baseline()
        replay = ReplayResult(
            schema_version=1,
            skill_name="demo",
            skill_path="/skills/demo/SKILL.md",
            replayed_at="2026-07-15T00:00:00.000Z",
            full_capability_surface=[
                CapabilityEntry(tool="fs.read", source="declared"),
                CapabilityEntry(tool="exec.shell", source="inferred"),
            ],
            fixtures=[_fixture("f1", "summarize a PR diff", [{"tool": "fs.read"}])],
        )
        report = diff_all(baseline, replay)
        assert report.summary.pass_count == 1
        assert report.summary.drift == 0
        assert len(report.surface_changes) == 1
        assert report.exit_code == 1

    def test_missing_fixture_from_replay_is_drift(self):
        baseline = _make_baseline()
        replay = ReplayResult(
            schema_version=1,
            skill_name="demo",
            skill_path="/skills/demo/SKILL.md",
            replayed_at="2026-07-15T00:00:00.000Z",
            full_capability_surface=[CapabilityEntry(tool="fs.read", source="declared")],
            fixtures=[],
        )
        report = diff_all(baseline, replay)
        assert report.results[0].verdict == "DRIFT"
        assert report.exit_code == 1
