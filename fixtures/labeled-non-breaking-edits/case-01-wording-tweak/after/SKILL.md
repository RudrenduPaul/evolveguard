---
name: pr-summarizer
description: Produces a concise summary of a pull request's diff for a reviewer.
filesystem: read-only
scope: './workspace/**'
---

# PR Summarizer

Reads the changed files in a pull request and produces a short, plain-English
summary of what changed and why -- so a human reviewer has context before
opening the full diff.
