# Changelog

All notable changes to this project are documented in this file.

## 0.1.0 -- 2026-07-14

Initial release.

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
