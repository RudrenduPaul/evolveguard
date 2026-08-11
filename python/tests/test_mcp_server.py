"""Tests for the generic subprocess-wrapper MCP server (evolveguard.mcp_server).

The `run` tool shells out to the installed `evolveguard` CLI, so these tests
patch `subprocess.run` rather than requiring a real installed console
script -- keeping them independent of whatever happens to be on PATH in CI.
"""
from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import patch

from evolveguard import mcp_server


def _fake_completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=["evolveguard"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_tool_is_registered():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {"run"}


def test_run_returns_stdout_and_stderr_on_success():
    with patch("subprocess.run", return_value=_fake_completed(0, "0.1.4\n", "")):
        result = mcp_server.run(["--version"])

    assert result["returncode"] == 0
    assert result["stdout"] == "0.1.4\n"
    assert "error" not in result


def test_run_parses_json_stdout_when_present():
    payload = '{"schemaVersion": 1, "exitCode": 0}'
    with patch("subprocess.run", return_value=_fake_completed(0, payload, "")):
        result = mcp_server.run(["report", "--json"])

    assert result["json"] == {"schemaVersion": 1, "exitCode": 0}


def test_run_leaves_json_key_absent_when_stdout_is_not_json():
    with patch("subprocess.run", return_value=_fake_completed(0, "not json output\n", "")):
        result = mcp_server.run(["check", "./SKILL.md"])

    assert "json" not in result
    assert result["stdout"] == "not json output\n"


def test_run_returns_error_dict_on_non_zero_exit():
    with patch("subprocess.run", return_value=_fake_completed(2, "", "usage error\n")):
        result = mcp_server.run(["bogus-subcommand"])

    assert result["error"] == "usage error"
    assert result["returncode"] == 2


def test_run_returns_error_dict_when_binary_missing():
    with patch("subprocess.run", side_effect=OSError("no such file")):
        result = mcp_server.run(["--version"])

    assert "error" in result
    assert "evolveguard" in result["error"]


def test_run_returns_error_dict_on_timeout():
    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["evolveguard"], timeout=120),
    ):
        result = mcp_server.run(["check", "./SKILL.md"])

    assert "error" in result
    assert "timed out" in result["error"]


def test_build_description_falls_back_when_help_call_fails():
    with patch("subprocess.run", side_effect=OSError("no such file")):
        description = mcp_server._build_description()

    assert description == mcp_server._FALLBACK_DESCRIPTION


def test_build_description_uses_real_help_output_when_available():
    with patch("subprocess.run", return_value=_fake_completed(0, "usage: evolveguard ...", "")):
        description = mcp_server._build_description()

    assert "usage: evolveguard" in description
