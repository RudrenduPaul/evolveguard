"""
Human-readable output formatting for the CLI. Ported from
src/evolveguard-cli/formatters.ts.
"""
from __future__ import annotations

from typing import List

from . import __version__ as _VERSION
from .types import Baseline, CapabilityChange, EvolveGuardReport


def format_record_result(baseline: Baseline, baseline_path: str) -> str:
    lines: List[str] = []
    lines.append(f"EvolveGuard v{_VERSION} -- Baseline Recorded")
    lines.append(f"skill: {baseline.skill_name}  fixtures: {len(baseline.fixtures)}")
    lines.append("")
    for fixture in baseline.fixtures:
        tool_names = ", ".join(e.tool for e in fixture.tool_call_sequence) or (
            "(no capabilities detected)"
        )
        lines.append(f'  recorded  fixture: "{fixture.prompt}"  tools: {tool_names}')
    lines.append("")
    lines.append(f"baseline written to {baseline_path}")
    return "\n".join(lines)


def _summarize_change(change: CapabilityChange) -> str:
    if change.kind == "added":
        return f"new tool call: {change.tool} (baseline had none)"
    if change.kind == "removed":
        return f"tool call removed: {change.tool}"
    return f"scope changed: {change.tool}"


def format_check_result(report: EvolveGuardReport, baseline_recorded_at: str) -> str:
    lines: List[str] = []
    date = baseline_recorded_at[:10]
    lines.append(f"EvolveGuard v{_VERSION} -- Regression Check")
    lines.append(
        f"skill: {report.skill_name}  baseline: {date}  fixtures: {report.summary.total}"
    )
    lines.append("")

    for result in report.results:
        tag = "[PASS] " if result.verdict == "PASS" else "[DRIFT]"
        if result.verdict == "PASS":
            lines.append(f'{tag} fixture: "{result.prompt}"  tool-call sequence unchanged')
        else:
            first = result.changes[0] if result.changes else None
            summary = _summarize_change(first) if first else "behavior changed"
            lines.append(f'{tag} fixture: "{result.prompt}"  {summary}')
            for change in result.changes:
                lines.append(f"         -> {change.message}")

    if report.surface_changes:
        lines.append("")
        lines.append("skill-level surface changes (not tied to a specific fixture):")
        for change in report.surface_changes:
            lines.append(f"  -> {change.message}")

    lines.append("")
    lines.append(f"{report.summary.pass_count} PASS, {report.summary.drift} DRIFT, 0 FAIL")
    if report.exit_code == 1:
        lines.append("exit code 1 (DRIFT blocks merge by default; override with --allow-drift)")
    else:
        lines.append("exit code 0")

    return "\n".join(lines)


def format_report(report: EvolveGuardReport) -> str:
    lines: List[str] = []
    lines.append(f"EvolveGuard v{_VERSION} -- Report")
    lines.append(f"skill: {report.skill_name}  checked: {report.checked_at}")
    lines.append("")
    for result in report.results:
        lines.append(f"[{result.verdict}] {result.id}: {result.prompt}")
        for change in result.changes:
            lines.append(f"  -> {change.message}")
    if report.surface_changes:
        lines.append("")
        lines.append("skill-level surface changes:")
        for change in report.surface_changes:
            lines.append(f"  -> {change.message}")
    lines.append("")
    lines.append(f"{report.summary.pass_count} PASS, {report.summary.drift} DRIFT, 0 FAIL")
    lines.append(f"exit code {report.exit_code}")
    return "\n".join(lines)
