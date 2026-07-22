# Contributing

Thanks for looking at EvolveGuard. EvolveGuard ships two independently maintained,
equally first-class distributions of the same record/replay/diff pipeline: an npm
package (`evolveguard-cli`, TypeScript, repo root) and a PyPI package (`evolveguard-cli`,
Python, `python/`). Both parse the same skill-file frontmatter schema and are expected
to produce the same capability surface, and the same diff verdict, against the same
skill file and fixtures. Please read this whole file before opening a PR -- which
section applies depends on which codebase you're touching. This is a small, focused
CLI, so the bar for a contribution is mostly: does it work, is it tested, does it match
the existing style.

## Ground rules

- Every change lands with tests. Neither test suite is optional scaffolding -- both are
  the mechanism that keeps the two implementations in parity.
- A change to the frontmatter schema, the capability-surface derivation, or the diff
  verdict logic must be made in **both** `src/evolveguard/` (TypeScript) and
  `python/src/evolveguard/` (Python), with equivalent test coverage added to both
  suites. A behavior that only exists in one language is a silent gap between the two
  CLIs -- avoid it.
- Baseline and report JSON files must stay byte-compatible in shape between the two
  distributions (same camelCase keys, same `schemaVersion`) -- see
  [docs/concepts.md](./docs/concepts.md#file-formats-and-cross-distribution-compatibility)
  for why. A baseline recorded with one CLI must remain readable by the other.
- No `eval`/`exec`/dynamic `require`/`import` of anything read from a skill file or its
  hook scripts, in either codebase. EvolveGuard's entire premise is that it's safe to
  point it at a skill file that is itself the untested edit; a fix that breaks that
  invariant is not a fix.

## Working on the TypeScript package (repo root)

```bash
git clone https://github.com/RudrenduPaul/evolveguard.git
cd evolveguard
npm install
```

```bash
npx eslint .
npx prettier --check .
npx tsc --noEmit --strict
npx vitest run --coverage
npm audit --audit-level=high
```

All five must pass. Coverage on `src/evolveguard/**` must stay at or above 80% lines.

If your change touches `src/evolveguard/diff/` or `src/evolveguard/parser/skillmd.ts`
(the transcript-diff engine), also run the false-positive benchmark and report the
number in your PR description:

```bash
npx vitest run src/evolveguard/benchmark.test.ts
```

See `fixtures/labeled-non-breaking-edits/README.md` for what that corpus covers and how
to add a new labeled case.

TypeScript strict mode, ESLint + Prettier (config in `eslint.config.js` /
`.prettierrc.json`), vitest for tests. Keep new modules under `src/evolveguard/` (library)
or `src/evolveguard-cli/` (CLI), matching the existing `parser/` / `record/` / `replay/` /
`diff/` / `report/` split.

## Working on the Python package (`python/`)

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

- Source lives under `python/src/evolveguard/`, laid out to mirror the TypeScript
  module structure 1:1 (`parser/`, `record/`, `replay/`, `diff/`, `report/`, `cli.py`,
  `formatters.py`, `types.py`, `errors.py`, `paths.py`, `snapshot.py`, `fixtures.py`)
  so a change in one codebase has an obvious counterpart to check in the other.
- Tests use `pytest` (`python/tests/test_*.py`), including
  `tests/test_benchmark.py`, which runs the same false-positive benchmark as the
  TypeScript suite against the shared `fixtures/labeled-non-breaking-edits/` corpus at
  the repo root -- no fixture duplication, and it skips cleanly when run against a bare
  package install with no repo checkout alongside it.
- Build and verify a real install before opening a PR that touches packaging. Build the
  venv **outside** `python/` (a venv created inside the source tree can get bundled
  into the sdist by hatchling's default sdist target):
  ```bash
  python3 -m venv /tmp/eg-build && /tmp/eg-build/bin/pip install build
  /tmp/eg-build/bin/python -m build python --outdir python/dist
  python3 -m venv /tmp/eg-verify && /tmp/eg-verify/bin/pip install python/dist/*.whl
  /tmp/eg-verify/bin/evolveguard record fixtures/labeled-non-breaking-edits/case-01-wording-tweak/before/SKILL.md \
    --fixtures fixtures/labeled-non-breaking-edits/case-01-wording-tweak/fixtures.json \
    --baseline /tmp/eg-verify-baseline.json
  ```

## Adding or changing frontmatter fields or capability detection

1. Add the field/pattern to `src/evolveguard/parser/skillmd.ts` (TypeScript) and the
   matching `python/src/evolveguard/parser/skillmd.py` (Python) with equivalent regex
   semantics (JS regex syntax and Python `re` syntax are close but not identical --
   verify the translated pattern actually matches the same inputs, don't assume).
2. Add a positive test case and, where practical, a negative test case to both test
   suites (`src/evolveguard/parser/skillmd.test.ts` and `python/tests/test_skillmd.py`).
3. Run both test suites and both CLIs against a shared `fixtures/labeled-non-breaking-edits/`
   case to confirm the classification you'd expect on real content, not just unit-level
   assertions.

## Reporting bugs

Open a GitHub issue with the `SKILL.md` (or a minimal reproduction), which distribution
you're using (npm or PyPI), and the command you ran. A drift report you believe is
wrong is exactly the kind of issue that's useful -- please attach the
`evolveguard-report.json` it produced.

## Reporting a security issue

Do not open a public issue for a security vulnerability. See [SECURITY.md](./SECURITY.md).

## License

By contributing, you agree your contribution is licensed under the same MIT License
that covers the rest of this repository (see [LICENSE](./LICENSE)).
