---
name: workspace-cleaner
description: Deletes stale build artifacts across the repo.
filesystem: read-write
scope: './**'
---

# Workspace Cleaner

Removes stale build artifacts. Now scans the whole repo instead of just
the workspace directory, to catch stray artifacts left in other folders.
