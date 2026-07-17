"""Ported from src/evolveguard/parser/skillmd.test.ts."""
import os

import pytest

from evolveguard.parser.skillmd import (
    derive_capability_surface,
    infer_hook_evidence,
    parse_skill_file,
)
from evolveguard.types import DeclaredScope


class TestParseSkillFile:
    def test_parses_yaml_frontmatter_fields(self):
        content = (
            "---\n"
            "name: my-skill\n"
            "description: does a thing\n"
            "tools: [fs.read]\n"
            "network: true\n"
            "filesystem: read-write\n"
            'scope: "./workspace/**"\n'
            'hooks: ["hooks/pre.sh"]\n'
            "---\n\n"
            "Body text here.\n"
        )
        parsed = parse_skill_file(content, "SKILL.md")
        assert parsed.name == "my-skill"
        assert parsed.description == "does a thing"
        assert parsed.has_frontmatter is True
        assert parsed.declared_scope == DeclaredScope(
            tools=["fs.read"],
            network=True,
            filesystem="read-write",
            scope="./workspace/**",
            hooks=["hooks/pre.sh"],
        )
        assert parsed.body.strip() == "Body text here."

    def test_defaults_with_no_frontmatter(self):
        content = "Just prose, no frontmatter here."
        parsed = parse_skill_file(content, "MEMORY.md")
        assert parsed.name == "MEMORY"
        assert parsed.has_frontmatter is False
        assert parsed.declared_scope == DeclaredScope(
            tools=[], network=False, filesystem="none", scope="./**", hooks=[]
        )
        assert parsed.body == content

    def test_falls_back_to_file_base_name_if_no_name_field(self):
        content = "---\ndescription: no name here\n---\nbody"
        parsed = parse_skill_file(content, "/a/b/my-file.md")
        assert parsed.name == "my-file"

    def test_tolerates_malformed_yaml_without_throwing(self):
        content = "---\n: : not valid yaml : :\n---\nbody"
        parsed = parse_skill_file(content, "SKILL.md")
        assert parsed.has_frontmatter is True
        assert parsed.declared_scope.filesystem == "none"

    def test_rejects_unknown_filesystem_value(self):
        content = "---\nfilesystem: delete-everything\n---\nbody"
        parsed = parse_skill_file(content, "SKILL.md")
        assert parsed.declared_scope.filesystem == "none"


class TestDeriveCapabilitySurface:
    def test_includes_declared_tools_network_and_filesystem_scope(self, tmp_path):
        parsed = parse_skill_file(
            '---\ntools: [custom.tool]\nnetwork: true\nfilesystem: read-write\nscope: "./workspace/**"\n---\nbody',
            "SKILL.md",
        )
        surface = derive_capability_surface(parsed, str(tmp_path))
        tools = sorted(e.tool for e in surface)
        assert tools == ["custom.tool", "fs.read", "fs.write", "network.fetch"]
        fs_write = next(e for e in surface if e.tool == "fs.write")
        assert fs_write.source == "declared"
        assert fs_write.scope == "./workspace/**"

    def test_infers_network_fs_write_evidence_from_body(self, tmp_path):
        parsed = parse_skill_file(
            'This skill calls fetch("https://example.com") to sync state.', "MEMORY.md"
        )
        surface = derive_capability_surface(parsed, str(tmp_path))
        network_entry = next(e for e in surface if e.tool == "network.fetch")
        assert network_entry.source == "inferred"
        assert network_entry.evidence[0].file == "(body)"
        assert network_entry.evidence[0].line == 1

    def test_infers_evidence_from_bundled_hook_script(self, tmp_path):
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "pre.sh").write_text(
            "#!/bin/sh\ncurl https://example.com/upload\nrm -rf ./tmp\n"
        )
        parsed = parse_skill_file('---\nhooks: ["hooks/pre.sh"]\n---\nbody', "SKILL.md")
        surface = derive_capability_surface(parsed, str(tmp_path))
        network = next(e for e in surface if e.tool == "network.fetch")
        fs_write = next(e for e in surface if e.tool == "fs.write")
        assert network.source == "inferred"
        assert fs_write.source == "inferred"
        assert network.evidence[0].file == "hooks/pre.sh"

    def test_does_not_duplicate_declared_tool_as_inferred(self, tmp_path):
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "pre.sh").write_text("echo hi\n")
        parsed = parse_skill_file(
            '---\nfilesystem: read-write\nhooks: ["hooks/pre.sh"]\n---\n'
            "This skill uses fs.writeFileSync internally.",
            "SKILL.md",
        )
        surface = derive_capability_surface(parsed, str(tmp_path))
        fs_write_entries = [e for e in surface if e.tool == "fs.write"]
        assert len(fs_write_entries) == 1
        assert fs_write_entries[0].source == "declared"


class TestInferHookEvidence:
    def test_silently_skips_path_that_escapes_skill_directory(self, tmp_path):
        evidence = infer_hook_evidence(str(tmp_path), ["../../etc/passwd"])
        assert evidence["networkEvidence"] == []
        assert evidence["fsWriteEvidence"] == []

    def test_silently_skips_path_that_does_not_exist(self, tmp_path):
        evidence = infer_hook_evidence(str(tmp_path), ["does-not-exist.sh"])
        assert evidence["networkEvidence"] == []
        assert evidence["fsWriteEvidence"] == []

    def test_finds_no_evidence_in_clean_script(self, tmp_path):
        (tmp_path / "ok.sh").write_text("echo hello\n")
        evidence = infer_hook_evidence(str(tmp_path), ["ok.sh"])
        assert evidence["networkEvidence"] == []
        assert evidence["fsWriteEvidence"] == []
