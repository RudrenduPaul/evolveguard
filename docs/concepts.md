# Concepts

## The record -> replay -> diff pipeline

Both the npm and PyPI packages run the same pipeline (TypeScript:
`src/evolveguard/{record,replay,diff}/index.ts`; Python:
`evolveguard/{record,replay,diff}/__init__.py`):

```
record:
  SKILL.md/MEMORY.md + fixtures.json
       |
       v
  parse frontmatter (declared scope)  ->  scan body + hook scripts for
       |                                   static network/fs-write evidence
       v
  capability surface (declared + inferred entries)
       |
       v
  per-fixture tool-call snapshot (filtered by expectedToolCalls)
       |
       v
  Baseline written to disk (.evolveguard-baseline.json)

check:
  (possibly edited) SKILL.md/MEMORY.md + Baseline
       |
       v
  re-parse + re-derive capability surface (identical logic to record)
       |
       v
  re-snapshot each fixture from the baseline's own fixture list
       |
       v
  diff: per-fixture PASS/DRIFT + whole-surface change detection
       |
       v
  EvolveGuardReport -> exit code (0 PASS / 1 DRIFT / 2 usage error)
```

evolveguard never runs a live LLM agent and never replays a real
conversation transcript -- record and check are both fully static and
deterministic. A `Baseline`/`EvolveGuardReport` always comes back as a
structured value (or a specific `EvolveGuardError` for a usage problem),
never a silent partial result.

## What a "capability surface" is

A capability surface is a list of `CapabilityEntry` objects: `{tool,
source, scope?, evidence?}`. Every entry is either:

- **`declared`** -- read directly from the skill file's own YAML
  frontmatter (`tools`, `network`, `filesystem`, `scope`). A `filesystem:
  read-write` skill contributes both an `fs.read` and an `fs.write` entry,
  each scoped to the frontmatter's `scope` glob (default `./**`).
- **`inferred`** -- found by a read-only regex scan of the skill's body
  text and any bundled hook scripts referenced in `hooks:`. This is what
  lets evolveguard catch a capability a skill's frontmatter doesn't admit
  to -- e.g. a hook script that gained a `curl` call without the
  frontmatter's `network:` field ever changing. Inferred entries carry
  `evidence: [{file, line}]` citing exactly where the match was found.
  Evidence in the body itself is cited as `(body)`.

If a tool is both declared and has body/hook evidence, only the declared
entry is kept -- declared coverage takes precedence, and the inferred
evidence is redundant confirmation, not a second finding.

`MEMORY.md` files (Claude Code's auto-memory files) typically carry no
frontmatter at all. A file with no `---` frontmatter block is parsed with
an empty declared scope, so its entire capability surface comes from
inferred evidence in the body text -- this is exactly how evolveguard
supports `MEMORY.md` without a separate code path.

## Fixtures: filtering the surface per prompt

A fixtures file is a JSON array of `{id, prompt, expectedToolCalls?}`.
`expectedToolCalls` (each `{tool, scopeMatches?}`) filters the full
capability surface down to just the entries a given fixture author says
that prompt should touch:

- Omit `expectedToolCalls` entirely and the fixture snapshots the whole
  surface (a broad smoke-test fixture).
- Give specific `expectedToolCalls` and the fixture only snapshots surface
  entries matching those tool names (and, if `scopeMatches` is set, whose
  scope glob is compatible with it).

This matters because a per-fixture diff only ever compares the tools that
fixture declared it cares about -- a fixture expecting only `fs.read`
would never notice a brand-new `fs.write` capability on its own. That gap
is exactly what surface-level diffing (below) exists to close.

## Diff verdicts

- **Per-fixture** (`diffFixture`/`diff_fixture`): PASS if the baseline and
  replayed tool-call sequences match exactly (same tools, same scopes);
  DRIFT otherwise, with one `CapabilityChange` per difference --
  `added` (a new tool call appeared), `removed` (one disappeared), or
  `scope-changed` (same tool, different scope). Each change carries a
  specific, human-readable `message`, never a bare boolean.
- **Surface-level** (`diffSurface`/`diff_surface`): compares the *whole*
  recorded vs. replayed capability surface, independent of any fixture.
  This is what catches a new capability no fixture's `expectedToolCalls`
  happened to cover -- `diffAll`/`diff_all` filters out any tool a
  per-fixture diff already flagged, so a real change is never reported
  twice.
- **Report** (`diffAll`/`diff_all`): combines both into an
  `EvolveGuardReport` with a `summary` (`pass`/`drift`/`total`) and an
  `exitCode`: `0` if nothing drifted, `1` if either a fixture-level or a
  surface-level change was found (pass `--allow-drift` to still exit `0`
  while still reporting it), `2` for a usage/parse error before any
  diffing ran.

## Scope

evolveguard detects changes in what a skill is *declared or shown* to be
capable of -- a proxy for behavior, derived entirely from static analysis
of the skill artifact itself. It cannot tell you whether a live agent run
would actually behave differently on a given prompt; that would require
executing the skill against a real model, which is out of scope by
design (see the project README's FAQ and "How it's different" for the
comparison against Braintrust and agent-eval, which do run live agents).

## File formats and cross-distribution compatibility

`Baseline` and `EvolveGuardReport` are written as plain, pretty-printed
JSON with a `schemaVersion` field (currently `1`). Both distributions use
the exact same camelCase JSON key names (`skillName`, `recordedAt`,
`fullCapabilitySurface`, `toolCallSequence`, `expectedToolCalls`,
`scopeMatches`, `exitCode`, and so on), so a baseline recorded with the
Python CLI can be checked with the npm CLI and vice versa -- the file
format is the compatibility contract between the two packages, not the
runtime. Neither package ever uses `pickle` or another executable
serialization format for these files -- always plain JSON.
