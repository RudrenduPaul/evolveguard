import type {
  Baseline,
  CapabilityChange,
  CapabilityEntry,
  EvolveGuardReport,
  FixtureDiff,
  FixtureSnapshot,
  ReplayResult,
} from '../types';

/**
 * Compares one fixture's baseline tool-call sequence against its replayed
 * sequence and classifies the result. PASS = identical tool set and scopes.
 * DRIFT = a tool appeared that wasn't there before, a tool disappeared, or
 * a tool's scope changed -- each surfaced as a specific, cited change, per
 * the anti-sycophancy rule that a drift is a stated behavioral change, not
 * an unexplained failure.
 */
export function diffFixture(
  baselineFixture: FixtureSnapshot,
  replayedFixture: FixtureSnapshot
): FixtureDiff {
  const changes: CapabilityChange[] = [];

  const baselineByTool = new Map<string, CapabilityEntry>();
  for (const entry of baselineFixture.toolCallSequence) {
    baselineByTool.set(entry.tool, entry);
  }
  const replayedByTool = new Map<string, CapabilityEntry>();
  for (const entry of replayedFixture.toolCallSequence) {
    replayedByTool.set(entry.tool, entry);
  }

  for (const [tool, entry] of replayedByTool) {
    if (!baselineByTool.has(tool)) {
      changes.push({
        kind: 'added',
        tool,
        newScope: entry.scope,
        message: `new tool call: ${tool} (baseline had none) -- this edit introduces a capability the baseline never used`,
      });
    }
  }

  for (const [tool, entry] of baselineByTool) {
    if (!replayedByTool.has(tool)) {
      changes.push({
        kind: 'removed',
        tool,
        baselineScope: entry.scope,
        message: `tool call removed: ${tool} (baseline required this) -- this edit dropped a capability the baseline relied on`,
      });
    }
  }

  for (const [tool, baselineEntry] of baselineByTool) {
    const replayedEntry = replayedByTool.get(tool);
    if (!replayedEntry) continue;
    if (
      baselineEntry.scope &&
      replayedEntry.scope &&
      baselineEntry.scope !== replayedEntry.scope
    ) {
      changes.push({
        kind: 'scope-changed',
        tool,
        baselineScope: baselineEntry.scope,
        newScope: replayedEntry.scope,
        message: `scope changed for ${tool}: baseline "${baselineEntry.scope}" -> now "${replayedEntry.scope}"`,
      });
    }
  }

  return {
    id: baselineFixture.id,
    prompt: baselineFixture.prompt,
    verdict: changes.length === 0 ? 'PASS' : 'DRIFT',
    changes,
  };
}

/**
 * Diffs the skill's full capability surface (declared + inferred, across
 * the whole skill file) independent of any fixture. This is what catches a
 * new capability that no fixture's `expectedToolCalls` anticipated -- a
 * per-fixture diff alone can only ever compare the tools that fixture
 * declared it cares about.
 */
export function diffSurface(
  baselineSurface: CapabilityEntry[],
  replaySurface: CapabilityEntry[]
): CapabilityChange[] {
  const changes: CapabilityChange[] = [];

  const baselineByTool = new Map<string, CapabilityEntry>();
  for (const entry of baselineSurface) baselineByTool.set(entry.tool, entry);
  const replayedByTool = new Map<string, CapabilityEntry>();
  for (const entry of replaySurface) replayedByTool.set(entry.tool, entry);

  for (const [tool, entry] of replayedByTool) {
    if (!baselineByTool.has(tool)) {
      changes.push({
        kind: 'added',
        tool,
        newScope: entry.scope,
        message: `new capability on the skill surface: ${tool} (baseline had none) -- no fixture's expectedToolCalls covers this tool, so it would otherwise go unnoticed`,
      });
    }
  }

  for (const [tool, entry] of baselineByTool) {
    if (!replayedByTool.has(tool)) {
      changes.push({
        kind: 'removed',
        tool,
        baselineScope: entry.scope,
        message: `capability removed from the skill surface: ${tool} (baseline required this) -- this edit dropped a capability the baseline relied on`,
      });
    }
  }

  return changes;
}

/** Diffs every fixture in a baseline against its replayed counterpart and builds the full report. */
export function diffAll(
  baseline: Baseline,
  replay: ReplayResult,
  options: { allowDrift?: boolean } = {}
): EvolveGuardReport {
  const replayedById = new Map(replay.fixtures.map((f) => [f.id, f]));

  const results: FixtureDiff[] = baseline.fixtures.map((baselineFixture) => {
    const replayedFixture = replayedById.get(baselineFixture.id);
    if (!replayedFixture) {
      return {
        id: baselineFixture.id,
        prompt: baselineFixture.prompt,
        verdict: 'DRIFT',
        changes: [
          {
            kind: 'removed',
            tool: '(fixture missing)',
            message: `fixture "${baselineFixture.id}" is missing from the replay -- the baseline is stale or corrupted`,
          },
        ],
      };
    }
    return diffFixture(baselineFixture, replayedFixture);
  });

  // A capability change already surfaced through a per-fixture diff (above)
  // is not repeated here -- surfaceChanges exists specifically to catch a
  // change no fixture's expectedToolCalls covers, so entries for tools any
  // fixture already flagged are filtered out to avoid reporting the same
  // change twice.
  const toolsCoveredByFixtures = new Set(
    results.flatMap((r) => r.changes.map((c) => c.tool))
  );
  const surfaceChanges = diffSurface(
    baseline.fullCapabilitySurface,
    replay.fullCapabilitySurface
  ).filter((change) => !toolsCoveredByFixtures.has(change.tool));

  const pass = results.filter((r) => r.verdict === 'PASS').length;
  const drift = results.filter((r) => r.verdict === 'DRIFT').length;

  const anyDrift = drift > 0 || surfaceChanges.length > 0;
  const exitCode: 0 | 1 | 2 = anyDrift && !options.allowDrift ? 1 : 0;

  return {
    schemaVersion: 1,
    skillName: replay.skillName,
    skillPath: replay.skillPath,
    checkedAt: replay.replayedAt,
    results,
    surfaceChanges,
    summary: { pass, drift, total: results.length },
    exitCode,
  };
}
