---
name: changelog-writer
description: Writes a CHANGELOG entry from the latest commits and posts it to Slack.
filesystem: read-write
scope: './**'
network: false
hooks: ['hooks/format.sh']
---

# Changelog Writer

Reads recent commits and writes a formatted CHANGELOG.md entry locally,
then posts a copy to the team Slack channel.
