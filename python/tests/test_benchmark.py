"""
Runs EvolveGuard's own record -> replay -> diff pipeline against the
labeled corpus in fixtures/labeled-non-breaking-edits/ (at the repo root,
shared with the TypeScript test suite -- no fixture duplication) and
reports the false-positive rate: how often a case labeled "non-breaking"
is classified as DRIFT.

Benchmark command this number comes from:
    pytest tests/test_benchmark.py -v

This corpus lives at the repo root, not inside the published wheel/sdist
(same as skillguard's own examples/-based end-to-end suite), so this
module skips cleanly when run against a bare package install with no repo
checkout alongside it.

Ported from src/evolveguard/benchmark.test.ts.
"""
import json
import os

import pytest

from evolveguard.diff import diff_all
from evolveguard.record import record_baseline
from evolveguard.replay import replay_skill

_CORPUS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "labeled-non-breaking-edits")
)

pytestmark = pytest.mark.skipif(
    not os.path.isdir(_CORPUS_DIR),
    reason="labeled-non-breaking-edits corpus not present (not part of the published package)",
)


def _list_cases():
    return sorted(
        name
        for name in os.listdir(_CORPUS_DIR)
        if os.path.isdir(os.path.join(_CORPUS_DIR, name))
    )


def _run_case(case_name):
    case_dir = os.path.join(_CORPUS_DIR, case_name)
    before_path = os.path.join(case_dir, "before", "SKILL.md")
    after_path = os.path.join(case_dir, "after", "SKILL.md")
    fixtures_path = os.path.join(case_dir, "fixtures.json")

    baseline = record_baseline(before_path, fixtures_path)
    replay = replay_skill(after_path, baseline)
    report = diff_all(baseline, replay)

    return report.summary.drift > 0 or len(report.surface_changes) > 0


def _label(case_name):
    with open(os.path.join(_CORPUS_DIR, case_name, "label.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_corpus_has_both_classifications():
    assert len(_list_cases()) >= 4


@pytest.mark.parametrize("case_name", _list_cases() if os.path.isdir(_CORPUS_DIR) else [])
def test_case_classified_per_label(case_name):
    label = _label(case_name)
    has_drift = _run_case(case_name)
    if label["classification"] == "non-breaking":
        assert has_drift is False, f"{case_name} is labeled non-breaking but EvolveGuard flagged drift"
    else:
        assert has_drift is True, f"{case_name} is labeled breaking but EvolveGuard found no drift"


def test_zero_false_positive_rate_across_corpus():
    cases = _list_cases()
    non_breaking = [c for c in cases if _label(c)["classification"] == "non-breaking"]
    false_positives = [c for c in non_breaking if _run_case(c)]
    rate = len(false_positives) / len(non_breaking) if non_breaking else 0
    assert rate == 0
