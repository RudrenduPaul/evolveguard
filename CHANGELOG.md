# Changelog

All notable changes to this project are documented in this file. This changelog
covers both distributions -- the npm package (`evolveguard`, JS/TS, not yet
published) and the PyPI package (`evolveguard`, Python) -- since they implement the
same record/replay/diff pipeline; entries note which distribution they apply to.

## [Python 0.1.0] - 2026-07-17

Initial public release of the Python port, published to PyPI as `evolveguard`
(`pip install evolveguard`). Complementary to, not a replacement for, the npm
package once it publishes -- both will be first-class and maintained together. See
`python/README.md` for Python-specific usage.

### Added

- `evolveguard record`/`check`/`report`/`mcp` CLI (console script `evolveguard`,
  package `evolveguard`) with the same flags, defaults, and exit-code contract
  (`0` PASS, `1` DRIFT, `2` usage/parse error) as the npm CLI: `--fixtures`,
  `--baseline`, `--report`, `--allow-drift`, `--json`.
- Programmatic library API: `from evolveguard import record_baseline, replay_skill,
  diff_all, write_baseline, read_baseline, ...`, returning the same JSON-compatible
  dataclasses the CLI formats (`Baseline`, `ReplayResult`, `EvolveGuardReport`).
- The full record -> replay -> diff pipeline reimplemented as genuine Python logic:
  YAML frontmatter parsing (declared scope), static regex evidence scanning for
  inferred network/filesystem-write capabilities in skill body text and bundled hook
  scripts, per-fixture and whole-surface diffing.
- A first-party path-traversal guard (`resolve_within_base`) ported from
  `paths.ts`, including the symlink-escape re-check after the lexical containment
  check passes.
- Full pytest suite (67 tests) ported from the TypeScript vitest suite, covering the
  parser, snapshot builder, fixtures loader, record/replay/diff modules, baseline/
  report read-write with schema validation, the path guard, and the CLI, plus the
  same false-positive benchmark against `fixtures/labeled-non-breaking-edits/`.

### Notes

- Verified against the same `fixtures/labeled-non-breaking-edits/` corpus the
  TypeScript suite uses: identical PASS/DRIFT classification on all 5 labeled cases,
  0% false-positive rate (0 of 2 non-breaking cases flagged as drift), matching the
  npm package's own documented result.
- Verified byte-for-byte output parity against the npm CLI's own documented
  `case-03-add-write-capability` demo (the README's "What it does" example):
  identical `[DRIFT]` message, summary line, and exit code.

## 0.1.0 -- 2026-07-14

Initial release (npm/TypeScript).

- `evolveguard record` -- captures a golden-transcript baseline for a skill (`SKILL.md`
  or `MEMORY.md`) against a labeled fixtures file, snapshotting the skill's own declared
  (frontmatter) and inferred (static evidence in body text and bundled hook scripts)
  capability surface.
- `evolveguard check` -- re-parses the (possibly edited) skill, re-derives its capability
  surface, and diffs it against the baseline per fixture and at the whole-skill level.
  Exits 0 on PASS, 1 on DRIFT (override with `--allow-drift`), 2 on a usage or parse error.
- `evolveguard report` -- prints a previously written `evolveguard-report.json`.
- `--json` output mode on every subcommand.
- `evolveguard mcp` -- documented as not yet implemented; use `--json` output directly
  from an agent in the meantime.
- `fixtures/labeled-non-breaking-edits/` -- a labeled before/after corpus used to measure
  and report the false-positive rate on genuinely non-breaking edits (0% as of this release).
