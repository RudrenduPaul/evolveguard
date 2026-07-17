#!/usr/bin/env python3
"""
01 -- basic record/replay.

Demonstrates the core library call sequence: record_baseline() against a
skill and its labeled fixtures, then replay_skill() + diff_all() after an
edit, printing the human-readable verdict. Uses the repo's own bundled
fixtures/labeled-non-breaking-edits/case-03-add-write-capability/ corpus
case (a filesystem: read-only -> read-write edit -- the same "scan a
monorepo" example used in the project README's own quickstart), copied
into a scratch directory so running this script never modifies the repo's
fixtures.

Run:
    python3 examples/01-basic-record-replay/demo.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

from evolveguard import diff_all, record_baseline, replay_skill, write_baseline

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_DIR = (
    REPO_ROOT / "fixtures" / "labeled-non-breaking-edits" / "case-03-add-write-capability"
)


def main() -> int:
    if not CASE_DIR.exists():
        print(
            f"Fixture case not found at {CASE_DIR} -- run this from a full repo clone.",
            file=sys.stderr,
        )
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        skill_path = tmp_path / "SKILL.md"
        fixtures_path = tmp_path / "fixtures.json"
        shutil.copy(CASE_DIR / "before" / "SKILL.md", skill_path)
        shutil.copy(CASE_DIR / "fixtures.json", fixtures_path)

        baseline = record_baseline(str(skill_path), str(fixtures_path))
        write_baseline(str(tmp_path / ".evolveguard-baseline.json"), baseline)
        print(
            f"Recorded baseline for '{baseline.skill_name}': "
            f"{len(baseline.fixtures)} fixture(s)."
        )

        # ... the skill gets edited: filesystem widens from read-only to read-write ...
        shutil.copy(CASE_DIR / "after" / "SKILL.md", skill_path)

        replay = replay_skill(str(skill_path), baseline)
        report = diff_all(baseline, replay)

        print(f"\nCheck result: {report.summary.pass_count} PASS, {report.summary.drift} DRIFT")
        for result in report.results:
            print(f"  [{result.verdict}] {result.prompt}")
            for change in result.changes:
                print(f"    -> {change.message}")

        return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
