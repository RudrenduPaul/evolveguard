"""
Programmatic / agent-native entry point.

    from evolveguard import record_baseline, replay_skill, diff_all, write_baseline, read_baseline

    baseline = record_baseline("./SKILL.md", "./fixtures.json")
    write_baseline("./.evolveguard-baseline.json", baseline)

    # ... skill gets edited ...

    saved = read_baseline("./.evolveguard-baseline.json")
    replay = replay_skill("./SKILL.md", saved)
    report = diff_all(saved, replay)

Returns the same structured dataclasses the CLI formats for human/JSON
output -- an agent framework can call this in-process instead of shelling
out to the CLI. Same core record/replay/diff logic as the `evolveguard`
console script; evolveguard/cli.py is a thin argument-parsing wrapper over
these functions.

This is the Python port of the evolveguard npm package
(https://www.npmjs.com/package/evolveguard). Both distributions implement
the same golden-transcript record/replay/diff pipeline against a skill's
own declared and inferred capability surface; see
https://github.com/RudrenduPaul/evolveguard for the canonical
documentation, benchmarks, and the original TypeScript source.
"""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

from .diff import diff_all, diff_fixture, diff_surface
from .errors import EvolveGuardError, format_what_why_fix
from .fixtures import load_fixtures
from .parser.skillmd import (
    derive_capability_surface,
    infer_hook_evidence,
    parse_skill_file,
)
from .paths import resolve_cli_path, resolve_within_base
from .record import record_baseline
from .replay import replay_skill
from .report import read_baseline, read_report, write_baseline, write_report
from .snapshot import build_fixture_snapshots, load_skill
from .types import (
    Baseline,
    CapabilityChange,
    CapabilityEntry,
    DeclaredScope,
    EvidenceRef,
    EvolveGuardReport,
    ExpectedToolCall,
    Fixture,
    FixtureDiff,
    FixtureSnapshot,
    ParsedSkillFile,
    ReplayResult,
    Summary,
)

try:
    __version__ = _pkg_version("evolveguard-cli")
except PackageNotFoundError:
    # Package is not installed (e.g. running from a source checkout without
    # `pip install -e .`); fall back to a clearly-unresolved marker instead
    # of a stale hardcoded string.
    __version__ = "0.0.0+unknown"

__all__ = [
    "parse_skill_file",
    "derive_capability_surface",
    "infer_hook_evidence",
    "load_skill",
    "build_fixture_snapshots",
    "load_fixtures",
    "record_baseline",
    "replay_skill",
    "diff_fixture",
    "diff_all",
    "diff_surface",
    "write_baseline",
    "read_baseline",
    "write_report",
    "read_report",
    "EvolveGuardError",
    "format_what_why_fix",
    "resolve_within_base",
    "resolve_cli_path",
    "Baseline",
    "CapabilityChange",
    "CapabilityEntry",
    "DeclaredScope",
    "EvidenceRef",
    "EvolveGuardReport",
    "ExpectedToolCall",
    "Fixture",
    "FixtureDiff",
    "FixtureSnapshot",
    "ParsedSkillFile",
    "ReplayResult",
    "Summary",
    "__version__",
]
