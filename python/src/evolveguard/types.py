"""
Shared types for EvolveGuard's parse -> record -> replay -> diff pipeline.
Ported from src/evolveguard/types.ts.

Design note (see README "How it works"): EvolveGuard never invokes a live
LLM agent. A "capability surface" is a deterministic snapshot derived from
a skill file's own declared frontmatter scope plus static evidence found
in any bundled hook scripts it references -- the same static-analysis
mechanism SkillGuard uses for its declared-vs-actual scope check, applied
here to before/after comparison instead of security auditing.

Every dataclass below round-trips through `to_dict()`/`from_dict()` using
the exact same camelCase JSON key names the TypeScript package writes, so
a baseline or report file produced by one distribution (npm or PyPI) can
be read by the other -- schemaVersion is the compatibility contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceRef:
    """File:line evidence, present only for inferred entries."""

    file: str
    line: int

    def to_dict(self) -> Dict[str, Any]:
        return {"file": self.file, "line": self.line}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EvidenceRef":
        return EvidenceRef(file=d["file"], line=d["line"])


@dataclass
class CapabilityEntry:
    """A single capability a skill declares or is inferred to use."""

    tool: str
    source: str  # "declared" | "inferred"
    scope: Optional[str] = None
    evidence: Optional[List[EvidenceRef]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"tool": self.tool, "source": self.source}
        if self.scope is not None:
            d["scope"] = self.scope
        if self.evidence is not None:
            d["evidence"] = [e.to_dict() for e in self.evidence]
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CapabilityEntry":
        evidence = d.get("evidence")
        return CapabilityEntry(
            tool=d["tool"],
            source=d["source"],
            scope=d.get("scope"),
            evidence=[EvidenceRef.from_dict(e) for e in evidence]
            if evidence is not None
            else None,
        )


CapabilitySurface = List[CapabilityEntry]


@dataclass
class DeclaredScope:
    """Declared scope parsed directly out of a skill file's YAML frontmatter."""

    tools: List[str] = field(default_factory=list)
    network: bool = False
    filesystem: str = "none"  # "none" | "read-only" | "read-write"
    scope: str = "./**"
    hooks: List[str] = field(default_factory=list)


@dataclass
class ParsedSkillFile:
    name: str
    has_frontmatter: bool
    declared_scope: DeclaredScope
    body: str
    description: Optional[str] = None


@dataclass
class ExpectedToolCall:
    tool: str
    scope_matches: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"tool": self.tool}
        if self.scope_matches is not None:
            d["scopeMatches"] = self.scope_matches
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ExpectedToolCall":
        return ExpectedToolCall(tool=d["tool"], scope_matches=d.get("scopeMatches"))


@dataclass
class Fixture:
    """A single labeled fixture from the user-supplied fixtures.json."""

    id: str
    prompt: str
    expected_tool_calls: Optional[List[ExpectedToolCall]] = None


@dataclass
class FixtureSnapshot:
    """The tool-call sequence snapshot recorded (or replayed) for one fixture."""

    id: str
    prompt: str
    expected_tool_calls: List[ExpectedToolCall]
    tool_call_sequence: List[CapabilityEntry]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "expectedToolCalls": [e.to_dict() for e in self.expected_tool_calls],
            "toolCallSequence": [e.to_dict() for e in self.tool_call_sequence],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "FixtureSnapshot":
        return FixtureSnapshot(
            id=d["id"],
            prompt=d["prompt"],
            expected_tool_calls=[
                ExpectedToolCall.from_dict(e) for e in d.get("expectedToolCalls", [])
            ],
            tool_call_sequence=[
                CapabilityEntry.from_dict(e) for e in d.get("toolCallSequence", [])
            ],
        )


@dataclass
class Baseline:
    schema_version: int
    skill_name: str
    skill_path: str
    recorded_at: str
    full_capability_surface: List[CapabilityEntry]
    fixtures: List[FixtureSnapshot]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "skillName": self.skill_name,
            "skillPath": self.skill_path,
            "recordedAt": self.recorded_at,
            "fullCapabilitySurface": [e.to_dict() for e in self.full_capability_surface],
            "fixtures": [f.to_dict() for f in self.fixtures],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Baseline":
        return Baseline(
            schema_version=d["schemaVersion"],
            skill_name=d["skillName"],
            skill_path=d["skillPath"],
            recorded_at=d["recordedAt"],
            full_capability_surface=[
                CapabilityEntry.from_dict(e) for e in d.get("fullCapabilitySurface", [])
            ],
            fixtures=[FixtureSnapshot.from_dict(f) for f in d.get("fixtures", [])],
        )


@dataclass
class ReplayResult:
    schema_version: int
    skill_name: str
    skill_path: str
    replayed_at: str
    full_capability_surface: List[CapabilityEntry]
    fixtures: List[FixtureSnapshot]


@dataclass
class CapabilityChange:
    kind: str  # "added" | "removed" | "scope-widened" | "scope-changed"
    tool: str
    message: str
    baseline_scope: Optional[str] = None
    new_scope: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"kind": self.kind, "tool": self.tool, "message": self.message}
        if self.baseline_scope is not None:
            d["baselineScope"] = self.baseline_scope
        if self.new_scope is not None:
            d["newScope"] = self.new_scope
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CapabilityChange":
        return CapabilityChange(
            kind=d["kind"],
            tool=d["tool"],
            message=d["message"],
            baseline_scope=d.get("baselineScope"),
            new_scope=d.get("newScope"),
        )


@dataclass
class FixtureDiff:
    id: str
    prompt: str
    verdict: str  # "PASS" | "DRIFT"
    changes: List[CapabilityChange]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "verdict": self.verdict,
            "changes": [c.to_dict() for c in self.changes],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "FixtureDiff":
        return FixtureDiff(
            id=d["id"],
            prompt=d["prompt"],
            verdict=d["verdict"],
            changes=[CapabilityChange.from_dict(c) for c in d.get("changes", [])],
        )


@dataclass
class Summary:
    pass_count: int
    drift: int
    total: int

    def to_dict(self) -> Dict[str, Any]:
        return {"pass": self.pass_count, "drift": self.drift, "total": self.total}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Summary":
        return Summary(pass_count=d["pass"], drift=d["drift"], total=d["total"])


@dataclass
class EvolveGuardReport:
    schema_version: int
    skill_name: str
    skill_path: str
    checked_at: str
    results: List[FixtureDiff]
    surface_changes: List[CapabilityChange]
    summary: Summary
    exit_code: int  # 0 | 1 | 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "skillName": self.skill_name,
            "skillPath": self.skill_path,
            "checkedAt": self.checked_at,
            "results": [r.to_dict() for r in self.results],
            "surfaceChanges": [c.to_dict() for c in self.surface_changes],
            "summary": self.summary.to_dict(),
            "exitCode": self.exit_code,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EvolveGuardReport":
        return EvolveGuardReport(
            schema_version=d["schemaVersion"],
            skill_name=d["skillName"],
            skill_path=d["skillPath"],
            checked_at=d["checkedAt"],
            results=[FixtureDiff.from_dict(r) for r in d.get("results", [])],
            surface_changes=[
                CapabilityChange.from_dict(c) for c in d.get("surfaceChanges", [])
            ],
            summary=Summary.from_dict(d["summary"]),
            exit_code=d["exitCode"],
        )
