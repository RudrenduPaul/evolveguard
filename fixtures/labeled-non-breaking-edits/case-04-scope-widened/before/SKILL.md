---
name: workspace-cleaner
description: Deletes stale build artifacts inside the workspace directory.
filesystem: read-write
scope: './workspace/**'
---

# Workspace Cleaner

Removes stale build artifacts. Scoped to `./workspace/**` only -- never
touches anything outside the workspace directory.
