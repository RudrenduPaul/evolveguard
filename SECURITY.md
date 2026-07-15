# Security Policy

EvolveGuard reads local files you point it at (a `SKILL.md`/`MEMORY.md` file, a
fixtures JSON file, and any hook scripts a skill's frontmatter references) and never
executes any of them. It does not make network calls, does not run a live agent, and
does not send data anywhere. See the README's "How it works" section for the full
design.

## Reporting a vulnerability

If you find a security issue, please email rkpaul.venture@gmail.com with a description
of the issue and, if possible, steps to reproduce it. Do not open a public GitHub issue
for a security report.

We will acknowledge your report within a few days and aim to ship a fix or a documented
mitigation before any public disclosure.

## Scope notes

- **Path traversal:** hook script paths declared in a skill's frontmatter are resolved
  and validated against that skill's own directory (`src/evolveguard/paths.ts`) before
  being read -- a skill file cannot reference a path outside its own folder.
- **No code execution:** EvolveGuard never runs `eval`, never shells out to a
  subprocess, and never executes a skill's hook scripts. Capability detection is static
  regex evidence scanning of file contents only.
- **Untrusted skill content:** a skill file's own frontmatter and body are treated as
  untrusted input throughout the parser and capability-surface derivation -- malformed
  YAML, missing fields, and unexpected values all fail closed to safe defaults rather
  than throwing or executing anything.
