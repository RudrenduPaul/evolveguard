---
name: changelog-writer
description: Writes a CHANGELOG entry from the latest commits.
filesystem: read-write
scope: './**'
network: false
hooks: ['hooks/format.sh']
---

# Changelog Writer

Reads recent commits and writes a formatted CHANGELOG.md entry locally.
No network access.
