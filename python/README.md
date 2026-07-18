# evolveguard (Python) -- renamed to evolveguard-cli

**This PyPI package has been renamed.** Install [`evolveguard-cli`](https://pypi.org/project/evolveguard-cli/)
instead: `pip install evolveguard-cli`. This package will not receive further updates.

---

# evolveguard (Python)

Regression-testing CI gate for self-edited Claude Agent Skills -- `SKILL.md`
manifests and Claude Code auto-memory `MEMORY.md` files -- catching
behavioral drift before an edit ships.

[![PyPI version](https://img.shields.io/pypi/v/evolveguard.svg)](https://pypi.org/project/evolveguard/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/RudrenduPaul/evolveguard/blob/main/LICENSE)
[![Python versions](https://img.shields.io/pypi/pyversions/evolveguard.svg)](https://pypi.org/project/evolveguard/)
[![CI](https://github.com/RudrenduPaul/evolveguard/actions/workflows/ci.yml/badge.svg)](https://github.com/RudrenduPaul/evolveguard/actions/workflows/ci.yml)

## Why this exists

Claude Code's Agent Skills can be authored by a human, or by an agent
itself: `/skillify` turns a workflow into a `SKILL.md`, and the auto-memory
system in this same environment writes `MEMORY.md` files that quietly
change what an agent does in its next session. None of that gets a
regression check by default. A skill edit that breaks a working workflow
looks exactly like a skill edit that fixes one, until someone notices the
agent stopped doing something it used to do. evolveguard records a
baseline of a skill's own capability surface (what tools it's declared or
shown to use), then re-derives that surface every time the skill file
changes and diffs the result against the baseline: same tool-call
sequence, or a flagged drift with a specific reason.

## Install

```bash
pip install evolveguard
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv add evolveguard
```

> **Not yet live on PyPI.** The package is fully built, tested, and
> publish-ready (wheel + sdist built, inspected, and verified end to end
> from a fresh venv install), but the first `twine upload` on this account
> is currently blocked by PyPI's own new-project-creation anti-abuse
> throttle (`429 Too many new projects created`), confirmed across
> repeated upload attempts -- not a code or readiness issue. Until that
> clears, clone the repo and install from source:
>
> ```bash
> git clone https://github.com/RudrenduPaul/evolveguard.git
> cd evolveguard/python && pip install -e .
> ```

**About the npm package:** `evolveguard` is also registered as an npm
package name, but publishing it is currently blocked by a separate,
unrelated account-level 2FA constraint (the npm account's second factor is
security-key/passkey only, with no authenticator-app or OTP fallback
configured). Clone the repo and run `npm run build && npm link` if you
need the TypeScript CLI locally in the meantime.

## Quickstart

```bash
# 1. Record a baseline against a skill and its labeled fixtures
evolveguard record ./skills/my-skill/SKILL.md --fixtures ./fixtures/my-skill.json
# writes ./skills/my-skill/.evolveguard-baseline.json

# 2. Edit the skill (by hand, or let an agent edit it)

# 3. Check for drift
evolveguard check ./skills/my-skill/SKILL.md
# writes ./evolveguard-report.json, exits 1 if drift was found
```

A fixtures file is a JSON array of labeled prompts and the tool-call
shapes each one is expected to touch:

```json
[
  {
    "id": "scan-a-monorepo",
    "prompt": "scan a monorepo",
    "expectedToolCalls": [{ "tool": "fs.read" }, { "tool": "fs.write" }]
  }
]
```

`expectedToolCalls` is optional -- omit it and the fixture is treated as
exercising the skill's entire capability surface. `scopeMatches` (a glob)
narrows a tool to a specific filesystem scope, e.g.
`{ "tool": "fs.write", "scopeMatches": "./workspace/**" }`.

Or call the library directly (the agent-native path):

```python
from evolveguard import record_baseline, replay_skill, diff_all, write_baseline, read_baseline

baseline = record_baseline("./SKILL.md", "./fixtures.json")
write_baseline("./.evolveguard-baseline.json", baseline)

# ... skill gets edited ...

saved = read_baseline("./.evolveguard-baseline.json")
replay = replay_skill("./SKILL.md", saved)
report = diff_all(saved, replay)
print(report.summary, report.exit_code)
```

## How it works

evolveguard does not run a live LLM agent, and it does not replay a real
conversation transcript. It is a static, deterministic tool by design:

1. **`record`** parses a skill file's YAML frontmatter (declared `tools`,
   `network`, `filesystem`, `scope`, and any bundled `hooks`), scans the
   skill's body text and any hook scripts for static evidence of network
   calls or filesystem writes, and combines both into a **capability
   surface** -- the set of tools the skill is declared or shown to use.
   Each fixture's `expectedToolCalls` filters that surface down to the
   tools the fixture author says it cares about; the result is the
   recorded baseline.
2. **`check`** re-reads the (possibly edited) skill file, re-derives its
   capability surface with the exact same logic, and re-filters it per
   fixture.
3. **`diff`** compares baseline vs. current per fixture (PASS if the tool
   set and scopes match, DRIFT with a specific reason otherwise), and
   separately diffs the whole capability surface so a new capability that
   no fixture's `expectedToolCalls` happened to cover still gets caught.

evolveguard detects changes in what a skill is _declared or shown_ to be
capable of. It can't tell you whether a live agent run would actually
behave differently on a given prompt -- that's a real, intentional scope
limit. The tradeoff: it just needs a `SKILL.md` file and a fixtures file,
with nothing hosted and no SDK to integrate against, which is also why it
runs fully offline in a pre-commit hook or CI job. This Python package is
a genuine, independent port of the pipeline -- not a wrapper around the
Node binary. See the
[project README](https://github.com/RudrenduPaul/evolveguard#readme) for
the fuller design writeup and the comparison against Braintrust and
agent-eval.

## CLI command reference

```
usage: evolveguard [-h] [-V] {record,check,report,mcp} ...

Regression-testing CLI for self-edited Claude Agent Skills (SKILL.md,
MEMORY.md) -- golden-transcript record/replay against a skill's own
declared and inferred capability surface, zero hosted infrastructure.

positional arguments:
  {record,check,report,mcp}
    record              Record a golden-transcript baseline for a skill
                         against a set of labeled fixtures
    check               Replay the fixtures from a baseline against the
                         current (possibly edited) skill and report drift
    report              Print a previously generated evolveguard-report.json
    mcp                 [coming soon] Expose record/check/report as MCP
                         tools for a coding agent to call mid-session

options:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
```

`evolveguard record <skillPath> --fixtures <path> [--baseline <path>] [--json]`,
`evolveguard check <skillPath> [--baseline <path>] [--report <path>] [--allow-drift] [--json]`,
and `evolveguard report [reportPath] [--json]` mirror the npm CLI's flags
and defaults exactly -- see the
[project README's CLI reference](https://github.com/RudrenduPaul/evolveguard#cli-command-reference)
for the full `--help` output of each subcommand.

**Exit codes:** `0` all fixtures PASS and no surface-level drift, `1` at
least one DRIFT was found (pass `--allow-drift` to still exit 0 while
still reporting it), `2` a usage error or a file that failed to parse.

## Agent-native usage

Every subcommand supports `--json` for structured output an agent can
parse directly:

```bash
evolveguard check ./SKILL.md --json
```

`evolveguard mcp` is documented but not implemented yet in either
distribution -- call `record`/`check`/`report --json` directly as a
subprocess (or the library functions in-process) from your coding agent
until it ships.

## False-positive rate

No accuracy claim ships without the command that produced it. From a
clone of the repo:

```bash
cd python && pytest tests/test_benchmark.py -v
```

against `fixtures/labeled-non-breaking-edits/` (shared with the
TypeScript test suite, not duplicated) -- a small, hand-labeled corpus of
5 real before/after `SKILL.md` pairs: 2 labeled non-breaking (a wording
tweak, a typo fix) and 3 labeled breaking (a filesystem-scope widen, a new
write capability, and a hook script gaining a network call). As of this
release: **0% false positives** (0 of 2 non-breaking cases flagged as
drift), matching the npm package's own documented result on the same
corpus. The corpus is small and will grow as more real skill edits are
reported.

## Contributing

See [CONTRIBUTING.md](https://github.com/RudrenduPaul/evolveguard/blob/main/CONTRIBUTING.md).
There is no enforced minimum coverage threshold; the bar is that the full
pytest suite (`pytest` from `python/`) passes and new behavior ships with
tests.

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Security

evolveguard reads local files you point it at and never executes any of
them -- no `eval`, no subprocess, no dynamic import of scan-target
content, no network calls. Hook script paths declared in a skill's
frontmatter are resolved and validated against that skill's own directory
before being read, including a symlink-escape check, so a malicious or
broken skill file cannot make evolveguard read outside its own folder.
Baselines and reports are read and written as plain JSON, never pickled or
otherwise deserialized as executable data. See
[SECURITY.md](https://github.com/RudrenduPaul/evolveguard/blob/main/SECURITY.md)
for the disclosure process. **Honest note**: this project does not
currently publish SLSA provenance, Sigstore signatures, or an SBOM, and
has no OpenSSF Scorecard badge set up -- none of that infrastructure
exists yet for either distribution, so it isn't claimed here.

## License

MIT, see [LICENSE](https://github.com/RudrenduPaul/evolveguard/blob/main/LICENSE).
