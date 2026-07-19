#!/usr/bin/env python3
"""
Thin argument-parsing wrapper over evolveguard.record/replay/diff/report
(see those modules for the full record -> replay -> diff data flow). This
module owns: flag parsing, the WHAT/WHY/FIX error surface for bad CLI
input, and the process exit-code contract (0 all PASS, 1 at least one
DRIFT, 2 usage/parse error). Console entry point: `evolveguard <command>
[options]`, installed via the `evolveguard` console-script defined in
python/pyproject.toml.

Ported from src/evolveguard-cli/cli.ts (which uses `commander`); this port
uses the stdlib `argparse` to avoid a CLI-framework dependency. Flags,
defaults, subcommands, and the WHAT/WHY/FIX error text are kept identical
to the npm CLI's `--help` output and behavior. argparse's own usage-error
and --help/--version handling already raises SystemExit(2) / SystemExit(0)
respectively, which happens to match this CLI's documented exit-code
contract exactly, so run_cli() simply catches SystemExit around argument
parsing and returns the code instead of letting the process exit.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from . import __version__ as _VERSION
from .diff import diff_all
from .errors import EvolveGuardError, format_what_why_fix
from .formatters import format_check_result, format_record_result, format_report
from .record import record_baseline
from .replay import replay_skill
from .report import read_baseline, read_report, write_baseline, write_report

_DEFAULT_REPORT_PATH = "./evolveguard-report.json"

_DESCRIPTION = (
    "Regression-testing CLI for self-edited Claude Agent Skills (SKILL.md, "
    "MEMORY.md) -- golden-transcript record/replay against a skill's own "
    "declared and inferred capability surface, zero hosted infrastructure."
)


def _default_baseline_path(skill_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(skill_path)), ".evolveguard-baseline.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evolveguard", description=_DESCRIPTION)
    parser.add_argument(
        "-V", "--version", action="version", version=f"evolveguard {_VERSION}"
    )

    subparsers = parser.add_subparsers(dest="command")

    record_parser = subparsers.add_parser(
        "record",
        help="Record a golden-transcript baseline for a skill against a set of labeled fixtures",
    )
    record_parser.add_argument(
        "skill_path", metavar="skillPath", help="path to the SKILL.md or MEMORY.md file to baseline"
    )
    record_parser.add_argument(
        "--fixtures",
        required=True,
        metavar="<path>",
        help="path to a fixtures JSON file (array of {id, prompt, expectedToolCalls?})",
    )
    record_parser.add_argument(
        "--baseline",
        default=None,
        metavar="<path>",
        help="path to write the baseline file (default: <skill-dir>/.evolveguard-baseline.json)",
    )
    record_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="output structured JSON instead of human-readable text (default: false)",
    )

    check_parser = subparsers.add_parser(
        "check",
        help="Replay the fixtures from a baseline against the current (possibly edited) skill and report drift",
    )
    check_parser.add_argument(
        "skill_path", metavar="skillPath", help="path to the SKILL.md or MEMORY.md file to check"
    )
    check_parser.add_argument(
        "--baseline",
        default=None,
        metavar="<path>",
        help="path to the baseline file (default: <skill-dir>/.evolveguard-baseline.json)",
    )
    check_parser.add_argument(
        "--report", default=_DEFAULT_REPORT_PATH, metavar="<path>", help="path to write the report file"
    )
    check_parser.add_argument(
        "--allow-drift",
        action="store_true",
        default=False,
        help="exit 0 even if drift is detected (drift is still reported) (default: false)",
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="output structured JSON instead of human-readable text (default: false)",
    )

    report_parser = subparsers.add_parser(
        "report", help="Print a previously generated evolveguard-report.json"
    )
    report_parser.add_argument(
        "report_path",
        metavar="reportPath",
        nargs="?",
        default=_DEFAULT_REPORT_PATH,
        help="path to the report file",
    )
    report_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="output structured JSON instead of human-readable text (default: false)",
    )

    subparsers.add_parser(
        "mcp",
        help="[coming soon] Expose record/check/report as MCP tools for a coding agent to call mid-session",
    )

    return parser


def _handle_error(err: Exception) -> int:
    if isinstance(err, EvolveGuardError):
        sys.stderr.write(str(err) + "\n")
        return 2
    sys.stderr.write(
        format_what_why_fix(
            "evolveguard crashed unexpectedly.",
            str(err),
            "Please open an issue at https://github.com/RudrenduPaul/evolveguard/issues "
            "with the command you ran.",
        )
        + "\n"
    )
    return 2


def _run_record(args: argparse.Namespace) -> int:
    try:
        baseline = record_baseline(args.skill_path, args.fixtures)
        baseline_path = args.baseline or _default_baseline_path(args.skill_path)
        write_baseline(baseline_path, baseline)

        if args.json:
            sys.stdout.write(
                json.dumps(
                    {"baseline": baseline.to_dict(), "baselinePath": baseline_path}, indent=2
                )
                + "\n"
            )
        else:
            sys.stdout.write(format_record_result(baseline, baseline_path) + "\n")
        return 0
    except Exception as err:  # noqa: BLE001 -- top-level command error guard, mirrors src/cli.ts
        return _handle_error(err)


def _run_check(args: argparse.Namespace) -> int:
    try:
        baseline_path = args.baseline or _default_baseline_path(args.skill_path)
        baseline = read_baseline(baseline_path)
        replay = replay_skill(args.skill_path, baseline)
        report = diff_all(baseline, replay, allow_drift=args.allow_drift)
        write_report(args.report, report)

        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2) + "\n")
        else:
            sys.stdout.write(format_check_result(report, baseline.recorded_at) + "\n")
        return report.exit_code
    except Exception as err:  # noqa: BLE001
        return _handle_error(err)


def _run_report(args: argparse.Namespace) -> int:
    try:
        report = read_report(args.report_path)
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2) + "\n")
        else:
            sys.stdout.write(format_report(report) + "\n")
        return report.exit_code
    except Exception as err:  # noqa: BLE001
        return _handle_error(err)


def run_cli(argv: List[str]) -> int:
    """
    `argv` follows the sys.argv convention: argv[0] is the program name,
    the real arguments start at argv[1]. Returns the process exit code.
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else 2)

    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "record":
        return _run_record(args)
    if args.command == "check":
        return _run_check(args)
    if args.command == "report":
        return _run_report(args)
    if args.command == "mcp":
        sys.stdout.write(
            "evolveguard mcp is not implemented yet. Use `evolveguard record`/`check`/"
            "`report --json` directly from an agent for now.\n"
        )
        return 0

    parser.print_help()
    return 2


def main() -> None:
    try:
        code = run_cli(sys.argv)
    except SystemExit:
        raise
    except Exception as err:  # noqa: BLE001 -- top-level crash guard, mirrors src/cli.ts's catch-all
        sys.stderr.write(
            format_what_why_fix(
                "evolveguard crashed unexpectedly.",
                str(err),
                "Please open an issue at https://github.com/RudrenduPaul/evolveguard/issues "
                "with the command you ran.",
            )
            + "\n"
        )
        sys.exit(2)
    else:
        sys.exit(code)


if __name__ == "__main__":
    main()
