# Getting started

evolveguard records a baseline of a Claude Agent Skill's own capability
surface (the tools it's declared or shown to use), then re-derives that
surface every time the skill file changes and diffs the result against the
baseline. It ships as two packages against the same pipeline: an npm
package (`evolveguard-cli`, JavaScript/TypeScript) and a PyPI package
(`evolveguard-cli`, Python).

## Install

**npm (JS/TS CLI):**

```bash
npm install -g evolveguard-cli
```

Live at [npmjs.com/package/evolveguard-cli](https://www.npmjs.com/package/evolveguard-cli).
Renamed 2026-07-19 from the old plain `evolveguard`, which is now
deprecated -- install `evolveguard-cli` instead. To install from source,
clone the repo and run `npm run build && npm link`.

**pip (Python library + CLI):**

```bash
pip install evolveguard-cli
```

Live at [pypi.org/project/evolveguard-cli](https://pypi.org/project/evolveguard-cli/).
The package was originally published under the plain name `evolveguard`;
that older PyPI project is retired and no longer receives updates. To
install from source, clone the repo and run `cd python && pip install -e .`.

Neither install makes a network call at record/check time -- both are
fully static, local tools by design (see "How it works" below).

## Your first record/check cycle

Both packages ship the repo's `fixtures/labeled-non-breaking-edits/`
corpus for a safe first run. Clone the repo (this corpus isn't bundled
inside the published npm tarball or PyPI wheel -- it's demo/test content,
not part of what ships to users):

```bash
git clone https://github.com/RudrenduPaul/evolveguard.git
cd evolveguard
```

Record a baseline against the "before" state of a real labeled case (a
skill whose `filesystem` frontmatter is `read-only`):

```bash
# Python CLI (after `pip install evolveguard-cli`)
evolveguard record fixtures/labeled-non-breaking-edits/case-03-add-write-capability/before/SKILL.md \
  --fixtures fixtures/labeled-non-breaking-edits/case-03-add-write-capability/fixtures.json \
  --baseline /tmp/eg-demo-baseline.json
```

Now check the "after" state (the same skill, with `filesystem` widened to
`read-write`) against that baseline:

```bash
evolveguard check fixtures/labeled-non-breaking-edits/case-03-add-write-capability/after/SKILL.md \
  --baseline /tmp/eg-demo-baseline.json
```

Real output:

```
EvolveGuard v0.1.0 -- Regression Check
skill: monorepo-scanner  baseline: 2026-07-17  fixtures: 1

[DRIFT] fixture: "scan a monorepo"  new tool call: fs.write (baseline had none)
         -> new tool call: fs.write (baseline had none) -- this edit introduces a capability the baseline never used

0 PASS, 1 DRIFT, 0 FAIL
exit code 1 (DRIFT blocks merge by default; override with --allow-drift)
```

Now try a genuinely non-breaking case (a wording tweak with no frontmatter
change, on the `pr-summarizer` skill in `case-01-wording-tweak`):

```bash
evolveguard record fixtures/labeled-non-breaking-edits/case-01-wording-tweak/before/SKILL.md \
  --fixtures fixtures/labeled-non-breaking-edits/case-01-wording-tweak/fixtures.json \
  --baseline /tmp/eg-demo-baseline-2.json
evolveguard check fixtures/labeled-non-breaking-edits/case-01-wording-tweak/after/SKILL.md \
  --baseline /tmp/eg-demo-baseline-2.json
```

Real output:

```
EvolveGuard v0.1.0 -- Regression Check
skill: pr-summarizer  baseline: 2026-07-17  fixtures: 1

[PASS]  fixture: "summarize a PR diff"  tool-call sequence unchanged

1 PASS, 0 DRIFT, 0 FAIL
exit code 0
```

Exit code `0` means no drift, `1` means at least one fixture (or the whole
capability surface) drifted from the baseline, `2` means a usage error or
a file that failed to parse.

## Using the library instead of the CLI

Both packages export a programmatic API for the same record/replay/diff
pipeline, for an agent framework that wants to call evolveguard in-process
instead of shelling out to a CLI binary.

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

**Python:**

```python
from evolveguard import record_baseline, replay_skill, diff_all, write_baseline, read_baseline

baseline = record_baseline("./SKILL.md", "./fixtures.json")
write_baseline("./.evolveguard-baseline.json", baseline)
# ... skill gets edited ...
saved = read_baseline("./.evolveguard-baseline.json")
replay = replay_skill("./SKILL.md", saved)
report = diff_all(saved, replay)
```

Both return the same JSON-compatible shape (`schemaVersion`, `results`,
`surfaceChanges`, `summary`, `exitCode`) -- a baseline or report file
written by one distribution can be read by the other. See
[concepts.md](./concepts.md) for the full data model.

## Next steps

- [concepts.md](./concepts.md) -- what a "capability surface" actually is,
  how declared vs. inferred entries are derived, and how the diff verdict
  is decided.
- [integrations/ci.md](./integrations/ci.md) -- wiring evolveguard into a
  CI pipeline as a merge gate.
- The [project README](../README.md) for the full comparison against
  Braintrust and agent-eval, and the false-positive benchmark.
