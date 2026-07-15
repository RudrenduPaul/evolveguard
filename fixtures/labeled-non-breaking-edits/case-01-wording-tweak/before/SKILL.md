---
name: pr-summarizer
description: Summarizes a pull request diff for a reviewer.
filesystem: read-only
scope: './workspace/**'
---

# PR Summarizer

Reads the changed files in a pull request and writes a short summary of
what changed and why, for a human reviewer to read before diving into the
full diff.
