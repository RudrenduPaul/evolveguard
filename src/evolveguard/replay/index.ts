import { loadSkill, buildFixtureSnapshots } from '../snapshot';
import type { Baseline, Fixture, ReplayResult } from '../types';

/**
 * Re-parses the (possibly edited) skill file and re-derives its capability
 * surface using the exact same deterministic logic `record` used, then
 * re-snapshots each fixture from the baseline against the new surface. The
 * fixture list is taken from the baseline itself (not re-read from an
 * external fixtures.json) so `evolveguard check` only needs the skill path.
 */
export function replaySkill(skillPath: string, baseline: Baseline): ReplayResult {
  const skill = loadSkill(skillPath);

  const fixtures: Fixture[] = baseline.fixtures.map((f) => ({
    id: f.id,
    prompt: f.prompt,
    expectedToolCalls: f.expectedToolCalls,
  }));

  const fixtureSnapshots = buildFixtureSnapshots(skill.capabilitySurface, fixtures);

  return {
    schemaVersion: 1,
    skillName: skill.name,
    skillPath: skill.skillPath,
    replayedAt: new Date().toISOString(),
    fullCapabilitySurface: skill.capabilitySurface,
    fixtures: fixtureSnapshots,
  };
}
