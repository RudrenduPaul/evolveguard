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

_FALLBACK_DESCRIPTION = (
    "Run an evolveguard CLI command. `args` is the exact argv you would "
    'pass to the `evolveguard` command line tool, e.g. ["check", '
    '"./SKILL.md", "--json"]. Subcommands: record (baseline a skill '
    "against a fixtures file), check (replay fixtures against the current "
    "skill and report drift), report (print a saved evolveguard-report.json). "
    "Pass --json to record/check/report for structured output. Returns "
    "{returncode, stdout, stderr, json?} on success, or {error: ...} if the "
    "command could not be run, timed out, or exited non-zero."
)


def _build_description() -> str:
    """Builds the `run` tool description from the CLI's real `--help`
    output at import time, so the tool description stays accurate as
    subcommands are added. Falls back to a static description if the
    subprocess call fails for any reason (binary missing, not executable,
    non-zero exit, timeout)."""
    try:
        proc = subprocess.run(
            [_CLI_BIN, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        help_text = (proc.stdout or proc.stderr or "").strip()
        if not help_text:
            return _FALLBACK_DESCRIPTION
        return (
            "Run an evolveguard CLI command. `args` is the exact argv you "
            "would pass to the `evolveguard` command line tool "
            '(e.g. ["check", "./SKILL.md", "--json"]).\n\n'
            f"Real `evolveguard --help` output:\n{help_text}"
        )
    except (OSError, subprocess.TimeoutExpired):
        return _FALLBACK_DESCRIPTION


mcp = MCPServer("evolveguard")


@mcp.tool(description=_build_description())
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
