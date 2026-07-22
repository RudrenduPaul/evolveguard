# Security Policy

EvolveGuard reads local files you point it at (a `SKILL.md`/`MEMORY.md` file, a
fixtures JSON file, and any hook scripts a skill's frontmatter references) and never
executes any of them. It does not make network calls, does not run a live agent, and
does not send data anywhere. This applies identically to both distributions -- the npm
package (TypeScript) and the PyPI package (Python, `evolveguard-cli` on PyPI). See the
README's "How it works" section for the full design.

## Supported versions

| Package                   | Version | Supported |
| -------------------------- | ------- | --------- |
| `evolveguard-cli` (npm)  | 0.1.x   | Yes       |
| `evolveguard-cli` (PyPI) | 0.1.x   | Yes       |

Both distributions are pre-1.0 and under active development. Security fixes land on
the latest `0.1.x` release of each; there is no older supported line to backport to yet.
The old plain `evolveguard` name on both registries is deprecated (renamed to
`evolveguard-cli` 2026-07-19) and does not receive security updates -- install
`evolveguard-cli` instead.

## Reporting a vulnerability

If you find a security issue, please email rkpaul.venture@gmail.com with a description
of the issue, which distribution is affected (npm package, PyPI package, or both), and
if possible, steps to reproduce it. Do not open a public GitHub issue for a security
report.

We will acknowledge your report within a few days and aim to ship a fix or a documented
mitigation before any public disclosure.

## Scope notes

- **Path traversal:** hook script paths declared in a skill's frontmatter are resolved
  and validated against that skill's own directory (`src/evolveguard/paths.ts` /
  `python/src/evolveguard/paths.py`) before being read, including a symlink-escape
  re-check after the lexical containment check passes -- a skill file cannot reference
  a path outside its own folder, even via a symlink whose target lives elsewhere.
- **No code execution:** EvolveGuard never runs `eval`, never shells out to a
  subprocess, and never executes a skill's hook scripts, in either distribution.
  Capability detection is static regex evidence scanning of file contents only.
- **No insecure deserialization:** baselines and reports are read and written as plain
  JSON in both distributions -- never `pickle` or another executable serialization
  format -- so loading a baseline or report file, even a hand-edited or malformed one,
  cannot execute arbitrary code; it fails closed with a WHAT/WHY/FIX error instead.
- **Untrusted skill content:** a skill file's own frontmatter and body are treated as
  untrusted input throughout the parser and capability-surface derivation -- malformed
  YAML, missing fields, and unexpected values all fail closed to safe defaults rather
  than throwing or executing anything. The Python port uses `yaml.safe_load` (not
  `yaml.load`) specifically to avoid executing arbitrary YAML tags from untrusted
  frontmatter.
