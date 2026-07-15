---
name: monorepo-scanner
description: Scans a monorepo, reports a dependency inventory, and caches results to disk.
filesystem: read-write
scope: './**'
---

# Monorepo Scanner

Walks every package in a monorepo and reports what it finds. Now writes a
`.monorepo-scan-cache.json` file so repeat scans are faster.
