"""MCP server for evolveguard: a single generic `run` tool that shells out
to the installed `evolveguard` CLI, so an MCP-compatible agent can invoke
any evolveguard subcommand (record/check/report) without a bespoke tool per
subcommand. Requires the `mcp` extra (`pip install "evolveguard-cli[mcp]"`).
Started via `evolveguard-mcp` (stdio transport).

Uses `mcp.server.MCPServer`, the official SDK's current high-level server
class (`mcp` 2.0.0+); earlier 1.x releases exposed the same `.tool()`/
`.run()` pattern under the now-removed `mcp.server.fastmcp.FastMCP`.

Every tool handler here is wrapped so it cannot raise: subprocess launch
failures (OSError), timeouts, non-zero exit codes, and non-JSON stdout are
all converted into a returned `{"error": ...}` dict instead of an
exception, since an MCP tool that raises breaks the calling agent's turn.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from mcp.server import MCPServer

_CLI_BIN = shutil.which("evolveguard") or "evolveguard"
_TIMEOUT_SECONDS = 120

_DESCRIPTION = (
    "Runs the evolveguard CLI to detect capability drift in a Claude Agent Skill "
    "(SKILL.md) or Claude Code memory file (MEMORY.md) after it has been edited, by "
    "parsing its declared frontmatter scope and any static evidence of network or "
    "filesystem-write behavior, and diffing that capability surface against a "
    "previously recorded baseline. Call this before merging or accepting a "
    "human- or agent-authored edit to a skill/memory file, to catch a silent "
    "widening of what the skill is now capable of (e.g. a new fs.write call, a "
    "scope glob widened from ./workspace/** to ./**) before it ships. Do not call "
    "this for anything unrelated to SKILL.md/MEMORY.md capability regression, and "
    "do not expect it to catch behavioral drift that never touches the file's "
    "declared or inferred capability surface: evolveguard is purely static "
    "analysis, it never runs a live LLM agent, replays a real conversation, "
    "executes the skill's own hook scripts, or makes network calls.\n\n"
    "Prerequisites: a baseline must already exist for the target skill (create one "
    "first with a `record` call, which needs a fixtures JSON file of labeled "
    "prompts) before `check` is useful; `check` against a skill with no baseline "
    "will error. `report` only needs a previously written evolveguard-report.json.\n\n"
    "Side effects and idempotency: `record` writes a baseline JSON file (default "
    "<skill-dir>/.evolveguard-baseline.json, override with --baseline) and is "
    "idempotent -- re-running it overwrites the baseline with a fresh snapshot of "
    "the current file, it does not append or merge. `check` writes a report JSON "
    "file (default ./evolveguard-report.json, override with --report) and is "
    "read-only with respect to the skill/baseline files themselves; running it "
    "twice against unchanged inputs produces the same report. `report` only reads "
    "a file, it writes nothing. None of the three subcommands make network calls "
    "or execute any code from the skill file being analyzed. On failure (missing "
    "file, bad JSON, no baseline found), the CLI exits non-zero and this tool "
    "returns {error: ...} instead of raising, so a failed call never breaks your "
    "turn.\n\n"
    "`args` is the exact argv you would type after `evolveguard` on a command "
    "line, as a list of strings. Real examples pulled from this CLI's own --help:\n"
    '  ["record", "./skills/my-skill/SKILL.md", "--fixtures", "./fixtures/my-skill.json", "--json"]\n'
    '  ["check", "./skills/my-skill/SKILL.md", "--json"]\n'
    '  ["check", "./skills/my-skill/SKILL.md", "--allow-drift", "--json"]  # report drift but exit 0\n'
    '  ["report", "./evolveguard-report.json", "--json"]\n'
    "Append --json to any of record/check/report for structured output (recommended "
    "for programmatic use); omit it for human-readable text. Pass [\"--help\"] or "
    '["<subcommand>", "--help"] as args to discover the full flag set directly from '
    "the installed CLI.\n\n"
    "Exit codes surfaced via returncode: 0 = success (record: baseline written; "
    "check: all fixtures PASS, no surface drift; report: printed OK), 1 = check "
    "found DRIFT (blocks merge unless --allow-drift was passed), 2 = a usage error "
    "or a file that failed to parse. Return shape on success: {returncode: int, "
    "stdout: str, stderr: str, json?: {...}} where json is present only when stdout "
    "parsed as valid JSON (i.e. --json was passed). check --json's json payload has "
    "the shape {schemaVersion, skillName, results: [{id, verdict, changes}], "
    "surfaceChanges: [...], summary: {pass, drift, total}, exitCode}. On failure "
    "the return shape is {error: str, returncode?: int, stdout?: str, stderr?: str}."
)


mcp = MCPServer("evolveguard")


@mcp.tool(description=_DESCRIPTION)
def run(args: list[str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [_CLI_BIN, *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
        )
    except OSError as exc:
        return {"error": f"failed to launch the evolveguard CLI: {exc}"}
    except subprocess.TimeoutExpired:
        return {"error": f"evolveguard CLI timed out after {_TIMEOUT_SECONDS}s"}

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    if proc.returncode != 0:
        return {
            "error": stderr.strip() or stdout.strip() or f"evolveguard exited with code {proc.returncode}",
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    result: dict[str, Any] = {
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }
    if stdout.strip():
        try:
            result["json"] = json.loads(stdout)
        except json.JSONDecodeError:
            pass  # stdout wasn't JSON (e.g. --json wasn't passed); text is still in "stdout"
    return result


def main() -> None:
    """Entry point for the `evolveguard-mcp` console script."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
