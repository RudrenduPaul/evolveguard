"""
Reads and validates a user-supplied fixtures.json against the documented
schema: a non-empty JSON array of
{"id": string, "prompt": string, "expectedToolCalls"?: [{"tool": string, "scopeMatches"?: string}]}.
Ported from src/evolveguard/fixtures.ts (which uses zod; this port validates
by hand to avoid a schema-validation dependency).
"""
from __future__ import annotations

import json
from typing import Any, List

from .errors import EvolveGuardError
from .types import ExpectedToolCall, Fixture

_SCHEMA_HINT = (
    'A fixtures file is a non-empty JSON array of {"id": string, "prompt": string, '
    '"expectedToolCalls"?: [{"tool": string, "scopeMatches"?: string}]}.'
)


def _schema_error(fixtures_path: str, reason: str) -> EvolveGuardError:
    return EvolveGuardError(
        f'Fixtures file at "{fixtures_path}" does not match the expected schema.',
        reason,
        _SCHEMA_HINT,
    )


def _parse_expected_tool_call(raw: Any, index: int) -> ExpectedToolCall:
    if not isinstance(raw, dict):
        raise ValueError(f"expectedToolCalls[{index}]: expected an object")
    tool = raw.get("tool")
    if not isinstance(tool, str) or not tool:
        raise ValueError(f"expectedToolCalls[{index}].tool: expected a non-empty string")
    scope_matches = raw.get("scopeMatches")
    if scope_matches is not None and not isinstance(scope_matches, str):
        raise ValueError(f"expectedToolCalls[{index}].scopeMatches: expected a string")
    return ExpectedToolCall(tool=tool, scope_matches=scope_matches)


def _parse_fixture(raw: Any, index: int) -> Fixture:
    if not isinstance(raw, dict):
        raise ValueError(f"[{index}]: expected an object")
    fid = raw.get("id")
    if not isinstance(fid, str) or not fid:
        raise ValueError(f"[{index}].id: expected a non-empty string")
    prompt = raw.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise ValueError(f"[{index}].prompt: expected a non-empty string")

    raw_expected = raw.get("expectedToolCalls")
    if raw_expected is None:
        expected = None
    else:
        if not isinstance(raw_expected, list):
            raise ValueError(f"[{index}].expectedToolCalls: expected an array")
        expected = [
            _parse_expected_tool_call(item, i) for i, item in enumerate(raw_expected)
        ]

    return Fixture(id=fid, prompt=prompt, expected_tool_calls=expected)


def load_fixtures(fixtures_path: str) -> List[Fixture]:
    try:
        with open(fixtures_path, "r", encoding="utf-8") as fh:
            raw_text = fh.read()
    except OSError as err:
        raise EvolveGuardError(
            f'Could not read fixtures file at "{fixtures_path}".',
            str(err),
            "Pass a valid path to a fixtures JSON file with --fixtures.",
        ) from err

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as err:
        raise EvolveGuardError(
            f'Fixtures file at "{fixtures_path}" is not valid JSON.',
            str(err),
            "Fix the JSON syntax, e.g. run it through `python3 -m json.tool <file>`.",
        ) from err

    if not isinstance(parsed, list) or len(parsed) == 0:
        raise _schema_error(
            fixtures_path, "expected a non-empty array, got " + type(parsed).__name__
        )

    try:
        fixtures = [_parse_fixture(item, i) for i, item in enumerate(parsed)]
    except ValueError as err:
        raise _schema_error(fixtures_path, str(err)) from err

    ids = set()
    for fixture in fixtures:
        if fixture.id in ids:
            raise EvolveGuardError(
                f'Duplicate fixture id "{fixture.id}" in "{fixtures_path}".',
                "Fixture ids must be unique within a fixtures file -- they are used to "
                "match baseline entries on replay.",
                "Give each fixture a unique id.",
            )
        ids.add(fixture.id)

    return fixtures
