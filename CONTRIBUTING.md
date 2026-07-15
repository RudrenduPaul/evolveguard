# Contributing

Thanks for looking at EvolveGuard. This is a small, focused CLI, so the bar for a
contribution is mostly: does it work, is it tested, does it match the existing style.

## Setup

```bash
git clone https://github.com/RudrenduPaul/evolveguard.git
cd evolveguard
npm install
```

## Before opening a PR

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

## Code style

TypeScript strict mode, ESLint + Prettier (config in `eslint.config.js` /
`.prettierrc.json`), vitest for tests. Keep new modules under `src/evolveguard/` (library)
or `src/evolveguard-cli/` (CLI), matching the existing `parser/` / `record/` / `replay/` /
`diff/` / `report/` split.

## Reporting bugs

Open a GitHub issue with the `SKILL.md` (or a minimal reproduction) and the command you
ran. A drift report you believe is wrong is exactly the kind of issue that's useful --
please attach the `evolveguard-report.json` it produced.
