"""
Reads and writes baseline (.evolveguard-baseline.json) and report
(evolveguard-report.json) files as pretty-printed, deterministic JSON, with
schema validation on read. Ported from src/evolveguard/report/index.ts
(which uses zod; this port validates by hand to avoid a schema-validation
dependency).
"""
from __future__ import annotations

import json

from ..errors import EvolveGuardError
from ..types import Baseline, EvolveGuardReport


def write_baseline(baseline_path: str, baseline: Baseline) -> None:
    with open(baseline_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(baseline.to_dict(), indent=2) + "\n")


def read_baseline(baseline_path: str) -> Baseline:
    try:
        with open(baseline_path, "r", encoding="utf-8") as fh:
            raw_text = fh.read()
    except OSError as err:
        raise EvolveGuardError(
            f'Could not read baseline file at "{baseline_path}".',
            str(err),
            "Run `evolveguard record <SKILL.md> --fixtures <fixtures.json>` first to "
            "create a baseline.",
        ) from err

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as err:
        raise EvolveGuardError(
            f'Baseline file at "{baseline_path}" is not valid JSON.',
            str(err),
            "Re-run `evolveguard record` to regenerate the baseline file.",
        ) from err

    try:
        if not isinstance(parsed, dict) or parsed.get("schemaVersion") != 1:
            raise ValueError("missing or unexpected schemaVersion")
        if not parsed.get("fixtures"):
            raise ValueError("fixtures: expected a non-empty array")
        baseline = Baseline.from_dict(parsed)
    except (KeyError, ValueError, TypeError) as err:
        raise EvolveGuardError(
            f'Baseline file at "{baseline_path}" does not match the expected schema.',
            str(err),
            "Re-run `evolveguard record` to regenerate the baseline file, or check "
            "it was not hand-edited.",
        ) from err

    return baseline


def write_report(report_path: str, report: EvolveGuardReport) -> None:
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(report.to_dict(), indent=2) + "\n")


def read_report(report_path: str) -> EvolveGuardReport:
    try:
        with open(report_path, "r", encoding="utf-8") as fh:
            raw_text = fh.read()
    except OSError as err:
        raise EvolveGuardError(
            f'Could not read report file at "{report_path}".',
            str(err),
            "Run `evolveguard check <SKILL.md>` first to generate a report.",
        ) from err

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as err:
        raise EvolveGuardError(
            f'Report file at "{report_path}" is not valid JSON.',
            str(err),
            "Re-run `evolveguard check` to regenerate the report file.",
        ) from err

    try:
        if not isinstance(parsed, dict) or parsed.get("schemaVersion") != 1:
            raise ValueError("missing or unexpected schemaVersion")
        report = EvolveGuardReport.from_dict(parsed)
    except (KeyError, ValueError, TypeError) as err:
        raise EvolveGuardError(
            f'Report file at "{report_path}" does not match the expected schema.',
            str(err),
            "Re-run `evolveguard check` to regenerate the report file.",
        ) from err

    return report
