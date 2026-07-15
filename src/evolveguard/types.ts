/**
 * Shared types for EvolveGuard's parse -> record -> replay -> diff pipeline.
 *
 * Design note (see README "How it works"): EvolveGuard never invokes a live
 * LLM agent. A "capability surface" is a deterministic snapshot derived from
 * a skill file's own declared frontmatter scope plus static evidence found
 * in any bundled hook scripts it references -- the same static-analysis
 * mechanism SkillGuard uses for its declared-vs-actual scope check, applied
 * here to before/after comparison instead of security auditing.
 */

/** A single capability a skill declares or is inferred to use. */
export interface CapabilityEntry {
  /** e.g. "fs.read", "fs.write", "network.fetch", "exec.shell" */
  tool: string;
  /** Where this entry came from: the skill's own frontmatter, or static evidence in a hook script. */
  source: 'declared' | 'inferred';
  /** Glob scope this capability is limited to, if applicable (fs.* tools only). */
  scope?: string;
  /** File:line evidence, present only for inferred entries. */
  evidence?: EvidenceRef[];
}

export interface EvidenceRef {
  file: string;
  line: number;
}

export type CapabilitySurface = CapabilityEntry[];

/** Declared scope parsed directly out of a skill file's YAML frontmatter. */
export interface DeclaredScope {
  tools: string[];
  network: boolean;
  filesystem: 'none' | 'read-only' | 'read-write';
  scope: string;
  hooks: string[];
}

export interface ParsedSkillFile {
  /** Skill name from frontmatter `name:`, or the file's base name if absent (e.g. MEMORY.md has no frontmatter). */
  name: string;
  description?: string;
  hasFrontmatter: boolean;
  declaredScope: DeclaredScope;
  body: string;
}

/** A single labeled fixture from the user-supplied fixtures.json. */
export interface Fixture {
  id: string;
  prompt: string;
  expectedToolCalls?: ExpectedToolCall[];
}

export interface ExpectedToolCall {
  tool: string;
  /** Glob pattern the tool's scope must satisfy, if the tool is fs.read/fs.write. */
  scopeMatches?: string;
}

/** The tool-call sequence snapshot recorded (or replayed) for one fixture. */
export interface FixtureSnapshot {
  id: string;
  prompt: string;
  expectedToolCalls: ExpectedToolCall[];
  toolCallSequence: CapabilityEntry[];
}

export interface Baseline {
  schemaVersion: 1;
  skillName: string;
  skillPath: string;
  recordedAt: string;
  fullCapabilitySurface: CapabilitySurface;
  fixtures: FixtureSnapshot[];
}

export interface ReplayResult {
  schemaVersion: 1;
  skillName: string;
  skillPath: string;
  replayedAt: string;
  fullCapabilitySurface: CapabilitySurface;
  fixtures: FixtureSnapshot[];
}

export type FixtureVerdict = 'PASS' | 'DRIFT';

export interface FixtureDiff {
  id: string;
  prompt: string;
  verdict: FixtureVerdict;
  changes: CapabilityChange[];
}

export type CapabilityChangeKind =
  | 'added'
  | 'removed'
  | 'scope-widened'
  | 'scope-changed';

export interface CapabilityChange {
  kind: CapabilityChangeKind;
  tool: string;
  baselineScope?: string;
  newScope?: string;
  message: string;
}

export interface EvolveGuardReport {
  schemaVersion: 1;
  skillName: string;
  skillPath: string;
  checkedAt: string;
  results: FixtureDiff[];
  /**
   * Skill-level capability-surface changes not tied to any specific
   * fixture -- e.g. a brand-new tool call no fixture's `expectedToolCalls`
   * anticipated. Per-fixture diffing alone would miss this (a fixture only
   * ever sees the tools it declared it cares about), so this is always
   * computed against the full recorded/replayed surface, independent of
   * which fixtures exist.
   */
  surfaceChanges: CapabilityChange[];
  summary: {
    pass: number;
    drift: number;
    total: number;
  };
  /** 0 = all PASS, 1 = at least one DRIFT (unless --allow-drift), 2 = usage/parse error. */
  exitCode: 0 | 1 | 2;
}
