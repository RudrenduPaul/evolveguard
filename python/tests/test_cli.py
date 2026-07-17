"""Ported from src/evolveguard-cli/cli.test.ts."""
import json

from evolveguard.cli import run_cli


def _write_skill(tmp_path, content):
    p = tmp_path / "SKILL.md"
    p.write_text(content)
    return str(p)


def _write_fixtures(tmp_path, fixtures):
    p = tmp_path / "fixtures.json"
    p.write_text(json.dumps(fixtures))
    return str(p)


def test_record_writes_baseline_and_exits_0(tmp_path, capsys):
    skill_path = _write_skill(tmp_path, "---\nname: demo\nfilesystem: read-only\n---\nbody")
    fixtures_path = _write_fixtures(
        tmp_path, [{"id": "f1", "prompt": "read a file", "expectedToolCalls": [{"tool": "fs.read"}]}]
    )

    code = run_cli(["evolveguard", "record", skill_path, "--fixtures", fixtures_path])

    assert code == 0
    baseline_path = tmp_path / ".evolveguard-baseline.json"
    assert baseline_path.exists()
    assert "Baseline Recorded" in capsys.readouterr().out


def test_check_exits_0_with_pass_when_unchanged(tmp_path, capsys):
    skill_path = _write_skill(tmp_path, "---\nname: demo\nfilesystem: read-only\n---\nbody")
    fixtures_path = _write_fixtures(
        tmp_path, [{"id": "f1", "prompt": "read a file", "expectedToolCalls": [{"tool": "fs.read"}]}]
    )
    run_cli(["evolveguard", "record", skill_path, "--fixtures", fixtures_path])
    capsys.readouterr()

    report_path = str(tmp_path / "evolveguard-report.json")
    code = run_cli(["evolveguard", "check", skill_path, "--report", report_path])

    assert code == 0
    out = capsys.readouterr().out
    assert "[PASS]" in out
    assert (tmp_path / "evolveguard-report.json").exists()


def test_check_exits_1_with_drift_on_new_capability(tmp_path, capsys):
    skill_path = _write_skill(tmp_path, "---\nname: demo\nfilesystem: read-only\n---\nbody")
    fixtures_path = _write_fixtures(
        tmp_path,
        [
            {
                "id": "f1",
                "prompt": "scan a monorepo",
                "expectedToolCalls": [{"tool": "fs.read"}, {"tool": "fs.write"}],
            }
        ],
    )
    run_cli(["evolveguard", "record", skill_path, "--fixtures", fixtures_path])
    capsys.readouterr()

    with open(skill_path, "w") as fh:
        fh.write("---\nname: demo\nfilesystem: read-write\n---\nbody")

    report_path = str(tmp_path / "evolveguard-report.json")
    code = run_cli(["evolveguard", "check", skill_path, "--report", report_path])

    assert code == 1
    out = capsys.readouterr().out
    assert "[DRIFT]" in out
    assert "new tool call: fs.write" in out


def test_check_allow_drift_exits_0(tmp_path, capsys):
    skill_path = _write_skill(tmp_path, "---\nname: demo\nfilesystem: read-only\n---\nbody")
    fixtures_path = _write_fixtures(
        tmp_path,
        [
            {
                "id": "f1",
                "prompt": "scan a monorepo",
                "expectedToolCalls": [{"tool": "fs.read"}, {"tool": "fs.write"}],
            }
        ],
    )
    run_cli(["evolveguard", "record", skill_path, "--fixtures", fixtures_path])
    capsys.readouterr()
    with open(skill_path, "w") as fh:
        fh.write("---\nname: demo\nfilesystem: read-write\n---\nbody")

    report_path = str(tmp_path / "evolveguard-report.json")
    code = run_cli(
        ["evolveguard", "check", skill_path, "--allow-drift", "--report", report_path]
    )

    assert code == 0
    assert "[DRIFT]" in capsys.readouterr().out


def test_check_json_matches_report_schema(tmp_path, capsys):
    skill_path = _write_skill(tmp_path, "---\nname: demo\nfilesystem: read-only\n---\nbody")
    fixtures_path = _write_fixtures(
        tmp_path, [{"id": "f1", "prompt": "read a file", "expectedToolCalls": [{"tool": "fs.read"}]}]
    )
    run_cli(["evolveguard", "record", skill_path, "--fixtures", fixtures_path])
    capsys.readouterr()

    report_path = str(tmp_path / "evolveguard-report.json")
    code = run_cli(["evolveguard", "check", skill_path, "--json", "--report", report_path])

    assert code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["summary"] == {"pass": 1, "drift": 0, "total": 1}
    assert parsed["exitCode"] == 0


def test_report_prints_previously_written_report(tmp_path, capsys):
    skill_path = _write_skill(tmp_path, "---\nname: demo\nfilesystem: read-only\n---\nbody")
    fixtures_path = _write_fixtures(
        tmp_path, [{"id": "f1", "prompt": "read a file", "expectedToolCalls": [{"tool": "fs.read"}]}]
    )
    run_cli(["evolveguard", "record", skill_path, "--fixtures", fixtures_path])
    report_path = str(tmp_path / "evolveguard-report.json")
    run_cli(["evolveguard", "check", skill_path, "--report", report_path])
    capsys.readouterr()

    code = run_cli(["evolveguard", "report", report_path])

    assert code == 0
    assert "EvolveGuard" in capsys.readouterr().out


def test_check_exits_2_when_no_baseline(tmp_path, capsys):
    skill_path = _write_skill(tmp_path, "---\nname: demo\n---\nbody")
    code = run_cli(["evolveguard", "check", skill_path])
    assert code == 2
    err = capsys.readouterr().err
    assert "WHAT:" in err
    assert "WHY:" in err
    assert "FIX:" in err


def test_record_exits_2_when_fixtures_malformed(tmp_path, capsys):
    skill_path = _write_skill(tmp_path, "---\nname: demo\n---\nbody")
    bad_fixtures = tmp_path / "bad.json"
    bad_fixtures.write_text("{not json")

    code = run_cli(["evolveguard", "record", skill_path, "--fixtures", str(bad_fixtures)])

    assert code == 2
    assert "WHAT:" in capsys.readouterr().err


def test_mcp_prints_coming_soon_and_exits_0(capsys):
    code = run_cli(["evolveguard", "mcp"])
    assert code == 0
    assert "not implemented yet" in capsys.readouterr().out


def test_help_exits_0(capsys):
    code = run_cli(["evolveguard", "--help"])
    assert code == 0


def test_unknown_subcommand_exits_2(capsys):
    code = run_cli(["evolveguard", "not-a-real-command"])
    assert code == 2


def test_record_without_fixtures_exits_2(tmp_path, capsys):
    skill_path = _write_skill(tmp_path, "---\nname: demo\n---\nbody")
    code = run_cli(["evolveguard", "record", skill_path])
    assert code == 2
