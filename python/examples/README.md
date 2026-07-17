# Python examples

Each numbered subdirectory is a real, runnable script against the actual
`evolveguard` Python library (`from evolveguard import record_baseline,
...`), not pseudocode. They use the repo's own bundled corpus under
`../../fixtures/labeled-non-breaking-edits/`, so nothing external is
required.

Install the package first (editable install from this checkout, or `pip
install evolveguard` from PyPI both work identically):

```bash
cd python
pip install -e .
```

Then run any example directly:

```bash
python3 examples/01-basic-record-replay/demo.py
python3 examples/02-ci-gate/gate.py
python3 examples/02-ci-gate/gate.py --edited
python3 examples/03-agent-native-json/agent_report.py
```

| Example                                             | What it demonstrates                                                                                                                                                                                                |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [01-basic-record-replay](./01-basic-record-replay/) | The core library call sequence: `record_baseline()`, then `replay_skill()` + `diff_all()` after an edit, printing the human-readable PASS/DRIFT verdict.                                                            |
| [02-ci-gate](./02-ci-gate/)                         | Using evolveguard as a CI gate: record-if-missing on first run, check-and-propagate-exit-code on every later run -- suitable to drop into a CI script directly.                                                     |
| [03-agent-native-json](./03-agent-native-json/)     | The agent-native use case: calling evolveguard in-process (no CLI subprocess) and serializing the structured `EvolveGuardReport` to JSON, on a case only caught by inferred (static-evidence) capability detection. |
