# CI integrations

evolveguard is meant to be a CI gate on any pipeline where a Claude Agent
Skill (`SKILL.md`) or auto-memory file (`MEMORY.md`) can be edited by a
human or by an agent. The gate shape is always the same: a baseline is
recorded once (typically committed alongside the skill, or recorded in an
earlier pipeline step) and every subsequent `check` run diffs the current
file against it, failing the job on real exit code `1`.

## GitHub Actions -- Python CLI

Live on PyPI as `evolveguard-cli` (see the project README's Status
section) -- `pip install evolveguard-cli` works today, in CI or anywhere
else. To install from a repo checkout instead, use
`pip install git+https://github.com/RudrenduPaul/evolveguard.git#subdirectory=python`.

```yaml
name: evolveguard gate
on: [pull_request]

jobs:
  evolveguard-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install evolveguard-cli
      - name: Check skill for behavioral drift
        run: |
          evolveguard check skills/my-skill/SKILL.md \
            --baseline skills/my-skill/.evolveguard-baseline.json \
            --report evolveguard-report.json
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: evolveguard-report
          path: evolveguard-report.json
```

`evolveguard check` itself exits `1` on drift, so the step above already
fails the job with no extra gating logic needed -- the same real exit-code
contract the CLI documents (`0` PASS, `1` DRIFT, `2` usage/parse error).
The report artifact upload runs with `if: always()` so a failing check
still leaves the JSON report attached to the job for review, instead of
only a human-readable log line.

If a PR edit is expected to introduce a real, intentional capability
change (not a regression), re-record the baseline as part of that same PR
rather than reaching for `--allow-drift` as a default -- `--allow-drift`
still reports drift, it just doesn't fail the job, which is meant for a
transitional/monitoring period, not routine use.

```bash
evolveguard record skills/my-skill/SKILL.md \
  --fixtures skills/my-skill/fixtures.json \
  --baseline skills/my-skill/.evolveguard-baseline.json
git add skills/my-skill/.evolveguard-baseline.json
```

## GitHub Actions -- npm CLI

Live on npm as `evolveguard-cli` (see the project README's Status
section); there is no bundled composite Action yet, but installing and
running the CLI directly works today:

```yaml
- run: npm install -g evolveguard-cli
- run: evolveguard check skills/my-skill/SKILL.md --report evolveguard-report.json
```

Same flags, same exit-code contract as the Python CLI -- see
[concepts.md](../concepts.md#file-formats-and-cross-distribution-compatibility)
for why a baseline recorded with one CLI can be checked with the other.

## Pre-commit hook (Python CLI)

For a local/pre-push gate rather than CI, wire the Python CLI into
[pre-commit](https://pre-commit.com/):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: evolveguard
        name: evolveguard drift check
        entry: evolveguard check skills/my-skill/SKILL.md --baseline skills/my-skill/.evolveguard-baseline.json
        language: system
        pass_filenames: false
```

This assumes `evolveguard` is already on `PATH` (installed via `pip
install evolveguard-cli` in your dev environment), or use `language: python` /
`additional_dependencies: [evolveguard-cli]` instead if you want pre-commit to
manage the install itself.

## First-run bootstrap

`evolveguard check` fails with a `WHAT/WHY/FIX` usage error (exit code
`2`, not `1`) if no baseline file exists yet at the path it's looking for
-- this is deliberately distinct from a DRIFT verdict, since "no baseline
recorded yet" is a setup problem, not a regression. Record one first:

```bash
evolveguard record skills/my-skill/SKILL.md --fixtures skills/my-skill/fixtures.json
```

## Agent-native usage in a pipeline

Every subcommand supports `--json` for a coding agent (or another CI
script) to parse the result programmatically instead of scraping the
human-readable text:

```bash
evolveguard check skills/my-skill/SKILL.md --json | jq '.summary'
```

`evolveguard mcp` is documented but not implemented yet in either
distribution -- call `record`/`check`/`report --json` directly as a
subprocess (or the library functions in-process, see
[getting-started.md](../getting-started.md#using-the-library-instead-of-the-cli))
from an agent until it ships.
