---
name: monorepo-scanner
description: Scans a monorepo and reports a dependency inventory.
filesystem: read-only
scope: './**'
---

# Monorepo Scanner

Walks every package in a monorepo and reports what it finds. Read-only --
never writes to the repo it scans.
