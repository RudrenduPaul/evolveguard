#!/usr/bin/env python3
"""
02 -- CI gate.

Demonstrates using evolveguard as an actual CI gate script: on first run
(no baseline recorded yet in the scratch workspace) it records one and
exits 0; on every subsequent run it checks the current skill state against
that baseline and propagates the real evolveguard exit code as the process
exit code -- exactly what you'd drop into a CI pipeline step (see
../../../docs/integrations/ci.md for the GitHub Actions version of this
same pattern). Pass --edited on a second run to simulate the skill file
being edited (a filesystem scope widen from case-04-scope-widened) and see
a DRIFT verdict with a real nonzero exit code.

Run:
    python3 examples/02-ci-gate/gate.py
    python3 examples/02-ci-gate/gate.py --edited
"""
import shutil
import sys
import tempfile
from pathlib import Path

from evolveguard import diff_all, read_baseline, record_baseline, replay_skill, write_baseline, write_report

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_DIR = REPO_ROOT / "fixtures" / "labeled-non-breaking-edits" / "case-04-scope-widened"
WORKSPACE = Path(tempfile.gettempdir()) / "evolveguard-ci-gate-example"


def main() -> int:
    if not CASE_DIR.exists():
        print(
            f"Fixture case not found at {CASE_DIR} -- run this from a full repo clone.",
            file=sys.stderr,
        )
        return 2

    edited = "--edited" in sys.argv

    WORKSPACE.mkdir(exist_ok=True)
    skill_path = WORKSPACE / "SKILL.md"
    fixtures_path = WORKSPACE / "fixtures.json"
    baseline_path = WORKSPACE / ".evolveguard-baseline.json"
    report_path = WORKSPACE / "evolveguard-report.json"

    if not baseline_path.exists():
        shutil.copy(CASE_DIR / "before" / "SKILL.md", skill_path)
        shutil.copy(CASE_DIR / "fixtures.json", fixtures_path)
        baseline = record_baseline(str(skill_path), str(fixtures_path))
        write_baseline(str(baseline_path), baseline)
        print(f"No baseline found -- recorded one at {baseline_path}.")
        print("Run again (with --edited to simulate a scope-widening edit) to gate on it.")
        return 0

    if edited:
        shutil.copy(CASE_DIR / "after" / "SKILL.md", skill_path)

    baseline = read_baseline(str(baseline_path))
    replay = replay_skill(str(skill_path), baseline)
    report = diff_all(baseline, replay)
    write_report(str(report_path), report)

    if report.exit_code == 0:
        print(
            f"PASS: {baseline.skill_name} -- "
            f"{report.summary.pass_count}/{report.summary.total} fixtures unchanged."
        )
    else:
        print(
            f"DRIFT: {baseline.skill_name} -- {report.summary.drift} fixture(s) "
            "changed behavior.",
            file=sys.stderr,
        )
        for result in report.results:
            for change in result.changes:
                print(f"  -> {change.message}", file=sys.stderr)
        for change in report.surface_changes:
            print(f"  -> {change.message}", file=sys.stderr)

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
