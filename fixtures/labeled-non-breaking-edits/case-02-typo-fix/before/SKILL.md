---
name: secrets-scanner
description: Flags likely secrets committed to a repo.
filesystem: read-only
scope: './**'
---

# Secrets Scanner

Scans files for pattenrs that look like API keys, tokens, or credentials
and flags them for review. Does not modify any files.
