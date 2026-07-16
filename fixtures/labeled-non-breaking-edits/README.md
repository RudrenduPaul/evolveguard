# labeled-non-breaking-edits

A small corpus of real before/after `SKILL.md` pairs, each labeled `non-breaking`
or `breaking` by hand, used to measure EvolveGuard's false-positive rate: how
often a genuinely non-breaking edit gets flagged as DRIFT.

Each case directory contains:

- `before/SKILL.md` -- the skill file `evolveguard record` is run against
- `after/SKILL.md` -- the edited skill file `evolveguard check` is run against
- `fixtures.json` -- the fixtures used for both `record` and `check`
- `label.json` -- `{ "classification": "non-breaking" | "breaking", "reason": "..." }`

| Case                            | Classification | What changed                                                                                                                                                                            |
| ------------------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `case-01-wording-tweak`         | non-breaking   | Description and body prose reworded, no frontmatter change                                                                                                                              |
| `case-02-typo-fix`              | non-breaking   | Single-word typo fixed in body prose                                                                                                                                                    |
| `case-03-add-write-capability`  | breaking       | `filesystem: read-only` -> `read-write` (the same "scan a monorepo" example used in the README's own quickstart)                                                                        |
| `case-04-scope-widened`         | breaking       | `scope` widened from `./workspace/**` to `./**`                                                                                                                                         |
| `case-05-new-hook-network-call` | breaking       | Bundled hook script gains a `curl` call to an external webhook; declared `network:` frontmatter is unchanged, so this is only caught by inferred (static-evidence) capability detection |

Run `npx vitest run src/evolveguard/benchmark.test.ts` to regenerate the
false-positive rate against this corpus. As of this commit the rate is 0%
(0 of 2 non-breaking cases misclassified as DRIFT) -- see
`src/evolveguard/benchmark.test.ts` for the exact assertion.
