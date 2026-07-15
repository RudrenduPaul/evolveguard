import { loadSkill, buildFixtureSnapshots } from '../snapshot';
import { loadFixtures } from '../fixtures';
import type { Baseline } from '../types';

/**
 * Captures a golden-transcript baseline for a skill: parses the skill file,
 * derives its declared + inferred capability surface, and snapshots each
 * fixture's expected tool-call sequence against that surface. This never
 * invokes a live agent -- see README "How it works".
 */
export function recordBaseline(skillPath: string, fixturesPath: string): Baseline {
  const skill = loadSkill(skillPath);
  const fixtures = loadFixtures(fixturesPath);
  const fixtureSnapshots = buildFixtureSnapshots(skill.capabilitySurface, fixtures);

  return {
    schemaVersion: 1,
    skillName: skill.name,
    skillPath: skill.skillPath,
    recordedAt: new Date().toISOString(),
    fullCapabilitySurface: skill.capabilitySurface,
    fixtures: fixtureSnapshots,
  };
}
