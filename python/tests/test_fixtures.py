"""Ported from src/evolveguard/fixtures.test.ts."""
import json

import pytest

from evolveguard.errors import EvolveGuardError
from evolveguard.fixtures import load_fixtures


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_loads_a_well_formed_fixtures_file(tmp_path):
    p = _write(
        tmp_path,
        "good.json",
        json.dumps([{"id": "a", "prompt": "do a thing", "expectedToolCalls": [{"tool": "fs.read"}]}]),
    )
    fixtures = load_fixtures(p)
    assert len(fixtures) == 1
    assert fixtures[0].id == "a"


def test_allows_expected_tool_calls_to_be_omitted(tmp_path):
    p = _write(tmp_path, "minimal.json", json.dumps([{"id": "a", "prompt": "do a thing"}]))
    fixtures = load_fixtures(p)
    assert fixtures[0].expected_tool_calls is None


def test_missing_file_raises(tmp_path):
    with pytest.raises(EvolveGuardError):
        load_fixtures(str(tmp_path / "nope.json"))


def test_invalid_json_raises(tmp_path):
    p = _write(tmp_path, "bad.json", "{not json")
    with pytest.raises(EvolveGuardError):
        load_fixtures(p)


def test_empty_array_raises(tmp_path):
    p = _write(tmp_path, "empty.json", "[]")
    with pytest.raises(EvolveGuardError):
        load_fixtures(p)


def test_missing_required_field_raises(tmp_path):
    p = _write(tmp_path, "missing-field.json", json.dumps([{"id": "a"}]))
    with pytest.raises(EvolveGuardError):
        load_fixtures(p)


def test_duplicate_ids_raise(tmp_path):
    p = _write(
        tmp_path,
        "dupes.json",
        json.dumps([{"id": "a", "prompt": "one"}, {"id": "a", "prompt": "two"}]),
    )
    with pytest.raises(EvolveGuardError):
        load_fixtures(p)
