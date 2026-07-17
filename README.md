# evolveguard

[![CI](https://github.com/RudrenduPaul/evolveguard/actions/workflows/ci.yml/badge.svg)](https://github.com/RudrenduPaul/evolveguard/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/evolveguard.svg)](https://pypi.org/project/evolveguard/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Node](https://img.shields.io/badge/node-%3E%3D20.12-brightgreen)](package.json)

Catch behavioral drift when a Claude Agent Skill edits itself, before the edit ships.

```bash
# PyPI -- Python CLI + library (genuine port)
pip install evolveguard
```

```bash
# npm -- JavaScript/TypeScript CLI + library
npm install -g evolveguard
```

> Neither package is published yet, for two separate, unrelated reasons -- see
> [Status](#status) below for the full detail:
>
> - **npm** is blocked by an account-level constraint: this account's npm 2FA is
>   security-key/passkey-only with no authenticator-app or OTP fallback configured,
>   which blocks the `npm publish` step independent of the code itself.
> - **PyPI** is blocked by PyPI's own new-project-creation anti-abuse throttle
>   (`429 Too many new projects created`) on this account, confirmed across
>   repeated upload attempts -- also not a code issue.
>
> Until either clears, clone the repo: `npm run build && npm link` for the
> TypeScript CLI, or `cd python && pip install -e .` for the Python package. See
> [`python/README.md`](./python/README.md) for the Python-specific walkthrough.

---

Claude Code's Agent Skills can be authored by a human, or by an agent itself: `/skillify`
turns a workflow into a `SKILL.md`, and the auto-memory system in this same environment
writes `MEMORY.md` files that quietly change what an agent does in its next session.
None of that gets a regression check today. A skill edit that breaks a working workflow
looks exactly like a skill edit that fixes one, until someone notices the agent stopped
doing something it used to do.

evolveguard records a baseline of a skill's own capability surface (what tools it's
declared or shown to use), then re-derives that surface every time the skill file
changes and diffs the result against the baseline: same tool-call sequence, or a flagged
drift with a specific reason.

## What it does

```bash
evolveguard record ./SKILL.md --fixtures ./fixtures.json
# ... skill gets edited, by a human or an agent ...
evolveguard check ./SKILL.md
```

```
EvolveGuard v0.1.0 -- Regression Check
skill: monorepo-scanner  baseline: 2026-07-15  fixtures: 1

[DRIFT] fixture: "scan a monorepo"  new tool call: fs.write (baseline had none)
         -> new tool call: fs.write (baseline had none) -- this edit introduces a
            capability the baseline never used

0 PASS, 1 DRIFT, 0 FAIL
exit code 1 (DRIFT blocks merge by default; override with --allow-drift)
```

That's real output from this repo's own `fixtures/labeled-non-breaking-edits/case-03-add-write-capability/`
test case, wired to `filesystem: read-only` -> `read-write` in the skill's frontmatter.

## How it works

evolveguard does not run a live LLM agent, and it does not replay a real conversation
transcript. It is a static, deterministic tool by design:

1. **`record`** parses a skill file's YAML frontmatter (declared `tools`, `network`,
   `filesystem`, `scope`, and any bundled `hooks`), scans the skill's body text and any
   hook scripts for static evidence of network calls or filesystem writes, and combines
   both into a **capability surface** -- the set of tools the skill is declared or shown
   to use. Each fixture's `expectedToolCalls` filters that surface down to the tools the
   fixture author says it cares about; the result is the recorded baseline.
2. **`check`** re-reads the (possibly edited) skill file, re-derives its capability
   surface with the exact same logic, and re-filters it per fixture.
3. **`diff`** compares baseline vs. current per fixture (PASS if the tool set and scopes
   match, DRIFT with a specific reason otherwise), and separately diffs the _whole_
   capability surface so a new capability that no fixture's `expectedToolCalls` happened
   to cover still gets caught, instead of silently passing.

evolveguard detects changes in what a skill is _declared or shown_ to be capable of. It
can't tell you whether a live agent run would actually behave differently on a given
prompt -- that's a real, intentional scope limit. The tradeoff: it just needs a
`SKILL.md` file and a fixtures file, with nothing hosted and no SDK to integrate against,
which is also why it runs fully offline in a pre-commit hook or CI job.

## How it's different

**Braintrust** is a general LLM eval and observability platform. It is a strong choice
if you're already logging traces from a live agent and want statistical eval scoring
across runs, but it needs SDK integration and an eval-definition step per app. evolveguard
needs neither: point it at one `SKILL.md` file and a fixtures JSON, and it works.

**[agent-eval](https://github.com/RudrenduPaul/agent-eval)** (this same author's other
repo) answers a different, more general question: "did my agent's behavior change
between two versions I define," for any agent, framework-agnostic, requiring you to
stand up and run both versions yourself. evolveguard answers a narrower, structurally
different question, triggered directly by a file diff on `SKILL.md`/`MEMORY.md`: did
_this specific edit_ change the capability surface the baseline recorded. It parses the
skill artifact itself and never asks you to define or run anything live.

|                | evolveguard                                  | Braintrust                         | agent-eval                        |
| -------------- | -------------------------------------------- | ---------------------------------- | --------------------------------- |
| Setup          | `record` + `check` against one file          | SDK integration, eval definitions  | Define and run two agent versions |
| Trigger        | `SKILL.md`/`MEMORY.md` file diff             | Manual eval run                    | Manual A/B run                    |
| Mechanism      | Static capability-surface diff               | Live-run trace scoring             | Statistical behavior comparison   |
| Hosted infra   | None                                         | Hosted platform                    | None                              |
| Live LLM calls | None                                         | Yes (scores real runs)             | Yes (runs both versions)          |
| Best for       | Self-edited Claude Agent Skills specifically | General LLM app eval/observability | Any agent, generic A/B regression |

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

A fixtures file is a JSON array of labeled prompts and the tool-call shapes each one is
expected to touch:

```json
[
  {
    "id": "scan-a-monorepo",
    "prompt": "scan a monorepo",
    "expectedToolCalls": [{ "tool": "fs.read" }, { "tool": "fs.write" }]
  }
]
```

`expectedToolCalls` is optional -- omit it and the fixture is treated as exercising the
skill's entire capability surface. `scopeMatches` (a glob) narrows a tool to a specific
filesystem scope, e.g. `{ "tool": "fs.write", "scopeMatches": "./workspace/**" }`.

## CLI command reference

Generated from the actual `--help` output of the built CLI.

<details>
<summary><code>evolveguard --help</code></summary>

```
Usage: evolveguard [options] [command]

Regression-testing CLI for self-edited Claude Agent Skills (SKILL.md,
MEMORY.md) -- golden-transcript record/replay against a skill's own declared
and inferred capability surface, zero hosted infrastructure.

Options:
  -V, --version                  output the version number
  -h, --help                     display help for command

Commands:
  record [options] <skillPath>   Record a golden-transcript baseline for a
                                 skill against a set of labeled fixtures
  check [options] <skillPath>    Replay the fixtures from a baseline against
                                 the current (possibly edited) skill and report
                                 drift
  report [options] [reportPath]  Print a previously generated
                                 evolveguard-report.json
  mcp                            [coming soon] Expose record/check/report as
                                 MCP tools for a coding agent to call
                                 mid-session
  help [command]                 display help for command
```

</details>

<details>
<summary><code>evolveguard record --help</code></summary>

```
Usage: evolveguard record [options] <skillPath>

Record a golden-transcript baseline for a skill against a set of labeled
fixtures

Arguments:
  skillPath          path to the SKILL.md or MEMORY.md file to baseline

Options:
  --fixtures <path>  path to a fixtures JSON file (array of {id, prompt,
                     expectedToolCalls?})
  --baseline <path>  path to write the baseline file (default:
                     <skill-dir>/.evolveguard-baseline.json)
  --json             output structured JSON instead of human-readable text
                     (default: false)
  -h, --help         display help for command
```

</details>

<details>
<summary><code>evolveguard check --help</code></summary>

```
Usage: evolveguard check [options] <skillPath>

Replay the fixtures from a baseline against the current (possibly edited) skill
and report drift

Arguments:
  skillPath          path to the SKILL.md or MEMORY.md file to check

Options:
  --baseline <path>  path to the baseline file (default:
                     <skill-dir>/.evolveguard-baseline.json)
  --report <path>    path to write the report file (default:
                     "./evolveguard-report.json")
  --allow-drift      exit 0 even if drift is detected (drift is still reported)
                     (default: false)
  --json             output structured JSON instead of human-readable text
                     (default: false)
  -h, --help         display help for command
```

</details>

<details>
<summary><code>evolveguard report --help</code></summary>

```
Usage: evolveguard report [options] [reportPath]

Print a previously generated evolveguard-report.json

Arguments:
  reportPath  path to the report file (default: "./evolveguard-report.json")

Options:
  --json      output structured JSON instead of human-readable text (default:
              false)
  -h, --help  display help for command
```

</details>

**Exit codes:** `0` all fixtures PASS and no surface-level drift, `1` at least one DRIFT
was found (pass `--allow-drift` to still exit 0 while still reporting it), `2` a usage
error or a file that failed to parse.

## Agent-native usage

Every subcommand supports `--json` for structured output an agent can parse directly:

```bash
evolveguard check ./SKILL.md --json
```

```json
{
  "schemaVersion": 1,
  "skillName": "monorepo-scanner",
  "results": [
    {
      "id": "scan-a-monorepo",
      "verdict": "DRIFT",
      "changes": [
        /* ... */
      ]
    }
  ],
  "surfaceChanges": [],
  "summary": { "pass": 0, "drift": 1, "total": 1 },
  "exitCode": 1
}
```

`evolveguard mcp` is documented but not implemented yet -- see the CLI reference above.
Until it ships, call `record`/`check`/`report --json` directly as a subprocess from your
coding agent.

## Library API

evolveguard also exports a programmatic API for the same pipeline, if you'd rather
integrate it into your own tooling than shell out to the CLI. Both distributions
expose the same functions and the same JSON-compatible file format -- a baseline
recorded with one CLI can be checked with the other (see
[docs/concepts.md](./docs/concepts.md#file-formats-and-cross-distribution-compatibility)).

**TypeScript:**

```ts
import {
  recordBaseline,
  replaySkill,
  diffAll,
  writeBaseline,
  readBaseline,
} from 'evolveguard';

const baseline = recordBaseline('./SKILL.md', './fixtures.json');
writeBaseline('./.evolveguard-baseline.json', baseline);

// ... skill gets edited ...

const saved = readBaseline('./.evolveguard-baseline.json');
const replay = replaySkill('./SKILL.md', saved);
const report = diffAll(saved, replay);
```

See `src/evolveguard/index.ts` for the full exported surface: `parseSkillFile`,
`deriveCapabilitySurface`, `loadSkill`, `buildFixtureSnapshots`, `loadFixtures`,
`recordBaseline`, `replaySkill`, `diffFixture`, `diffAll`, `diffSurface`, `writeBaseline`,
`readBaseline`, `writeReport`, `readReport`, plus the shared `types.ts` interfaces.

**Python** (`pip install evolveguard`):

```python
from evolveguard import record_baseline, replay_skill, diff_all, write_baseline, read_baseline

baseline = record_baseline("./SKILL.md", "./fixtures.json")
write_baseline("./.evolveguard-baseline.json", baseline)

# ... skill gets edited ...

saved = read_baseline("./.evolveguard-baseline.json")
replay = replay_skill("./SKILL.md", saved)
report = diff_all(saved, replay)
```

See [`python/README.md`](./python/README.md) for the Python-specific walkthrough and
the same exported surface under `evolveguard/__init__.py`.

## False-positive rate

No accuracy claim ships without the command that produced it. Run:

```bash
npx vitest run src/evolveguard/benchmark.test.ts
```

against `fixtures/labeled-non-breaking-edits/` -- a small, hand-labeled corpus of real
before/after `SKILL.md` pairs (wording tweaks and typo fixes labeled non-breaking; a
filesystem-scope widen, a new write capability, and a hook script gaining a network call
labeled breaking). As of this commit: **0% false positives** (0 of 2 non-breaking cases
flagged as drift). The corpus is small and will grow as more real skill edits are
reported; see `fixtures/labeled-non-breaking-edits/README.md`.

## What is evolveguard, and why does it exist

evolveguard is a command-line tool and TypeScript library that detects capability drift
in Claude Agent Skill files (`SKILL.md`) and Claude Code auto-memory files (`MEMORY.md`)
after they are edited, by a human or by an agent. It works by parsing a skill's declared
frontmatter scope and any static evidence of network or filesystem-write behavior in its
body text and bundled hook scripts, snapshotting that as a baseline, and re-deriving the
same snapshot after an edit to diff against it. It exists because Claude Code's Agent
Skills ecosystem lets skills and memory files change an agent's behavior without a
human necessarily reviewing every edit for regression, and no existing tool checks that
specific artifact shape without requiring SDK integration or a live agent run.

## FAQ

**Does evolveguard call an LLM?**
No. Record and check are both fully static and deterministic -- see "How it works" above.

**Can it catch a change in what an agent actually decides to do on a given prompt?**
No, not directly. It catches changes in a skill's declared or inferred capability
surface (the tools it's allowed or shown to use), which is a proxy for behavior, not a
live trace of it. If you need to score actual agent runs, use Braintrust or agent-eval.

**Does it work with MEMORY.md files, which have no frontmatter?**
Yes. A file with no frontmatter is parsed with an empty declared scope, so its capability
surface comes entirely from static evidence found in the body text.

**Is this a general agent-evolution framework?**
No. See "How it's different" above -- evolveguard deliberately does not build or host a
self-evolving agent framework; it only tests skill/memory edits that already happened.

**Is this published on npm or PyPI yet?**
Not yet on either -- see [Status](#status) for the two separate, unrelated blockers.

## Status

This is a v0.1 release: a small, focused addition to the existing Claude Agent Skills
ecosystem. It ships fully MIT-licensed with no proprietary tier, as two independent,
equally first-class packages -- both fully built, tested, and publish-ready, blocked on
two separate account-level issues, neither a code problem:

- **PyPI (`evolveguard`, Python)** -- a genuine independent port, not a wrapper around
  the Node binary (see [`python/README.md`](./python/README.md)). Wheel and sdist are
  built, inspected, and verified end to end from a fresh venv install. The first
  `twine upload` on this account is blocked by PyPI's own new-project-creation
  anti-abuse throttle (`429 Too many new projects created`), confirmed across repeated
  upload attempts. It will publish as soon as that throttle clears; no code change is
  needed. Clone the repo and run `cd python && pip install -e .` in the meantime.
- **npm (`evolveguard`, TypeScript)** -- `npm pack --dry-run` passes clean and
  `package.json` metadata is publish-ready, but the actual `npm publish` is blocked on
  a separate account-level constraint: this npm account's 2FA is security-key/
  passkey-only, with no authenticator-app or OTP fallback configured, and npm currently
  requires completing that 2FA challenge interactively to publish. Clone the repo and
  run `npm run build && npm link` for the TypeScript CLI locally in the meantime.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
