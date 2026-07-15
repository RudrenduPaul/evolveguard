#!/bin/sh
# Formats the CHANGELOG entry locally, then posts it to Slack.
echo "Formatting changelog entry..."
curl -X POST https://hooks.slack.example.com/services/T000/B000/XXXX -d "$CHANGELOG_ENTRY"
