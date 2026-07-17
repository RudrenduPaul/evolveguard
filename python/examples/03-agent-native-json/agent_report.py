#!/usr/bin/env python3
"""
03 -- agent-native JSON.

Demonstrates the agent-native use case: calling evolveguard in-process (no
CLI subprocess) and serializing the structured EvolveGuardReport to JSON --
the same shape `evolveguard check --json` prints -- so a coding agent can
parse a regression verdict programmatically instead of scraping
human-readable text. Uses the repo's case-05-new-hook-network-call
fixture: a bundled hook script gains a curl call to an external webhook
while the skill's declared `network:` frontmatter stays unchanged, so this
is only caught by inferred (static-evidence) capability detection, not a
frontmatter diff.

Run:
    python3 examples/03-agent-native-json/agent_report.py
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

from evolveguard import diff_all, record_baseline, replay_skill

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_DIR = (
    REPO_ROOT / "fixtures" / "labeled-non-breaking-edits" / "case-05-new-hook-network-call"
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
        shutil.copytree(CASE_DIR / "before", tmp_path / "skill")
        shutil.copy(CASE_DIR / "fixtures.json", tmp_path / "fixtures.json")

        skill_path = tmp_path / "skill" / "SKILL.md"
        baseline = record_baseline(str(skill_path), str(tmp_path / "fixtures.json"))

        # ... the skill's bundled hook script gains a curl call to an external webhook ...
        shutil.rmtree(tmp_path / "skill")
        shutil.copytree(CASE_DIR / "after", tmp_path / "skill")

        replay = replay_skill(str(skill_path), baseline)
        report = diff_all(baseline, replay)

        # This is exactly the JSON `evolveguard check --json` prints -- an
        # agent can parse this directly instead of shelling out to the CLI.
        print(json.dumps(report.to_dict(), indent=2))

        return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
