import * as fs from 'node:fs';
import * as path from 'node:path';
import { minimatch } from 'minimatch';
import { parseSkillFile, deriveCapabilitySurface } from './parser/skillmd';
import type { CapabilitySurface, Fixture, FixtureSnapshot } from './types';
import { EvolveGuardError } from './errors';

export interface LoadedSkill {
  name: string;
  skillPath: string;
  skillDir: string;
  capabilitySurface: CapabilitySurface;
}

/** Reads a skill file from disk, parses it, and derives its full capability surface. */
export function loadSkill(skillPath: string): LoadedSkill {
  let content: string;
  try {
    content = fs.readFileSync(skillPath, 'utf8');
  } catch (err) {
    throw new EvolveGuardError(
      `Could not read skill file at "${skillPath}".`,
      err instanceof Error ? err.message : String(err),
      'Pass a valid path to a SKILL.md or MEMORY.md file.'
    );
  }

  const skillDir = path.dirname(path.resolve(skillPath));
  const parsed = parseSkillFile(content, skillPath);
  const capabilitySurface = deriveCapabilitySurface(parsed, skillDir);

  return {
    name: parsed.name,
    skillPath: path.resolve(skillPath),
    skillDir,
    capabilitySurface,
  };
}

/**
 * Builds the per-fixture tool-call sequence snapshot for a given capability
 * surface. A fixture with no `expectedToolCalls` is treated as exercising
 * the skill's entire surface (a broad smoke-test fixture); a fixture that
 * declares specific expected tool calls only snapshots the surface entries
 * matching those tools (and, if `scopeMatches` is given, only entries whose
 * declared/inferred scope satisfies that glob).
 */
export function buildFixtureSnapshots(
  surface: CapabilitySurface,
  fixtures: Fixture[]
): FixtureSnapshot[] {
  return fixtures.map((fixture) => {
    const expected = fixture.expectedToolCalls ?? [];

    if (expected.length === 0) {
      return {
        id: fixture.id,
        prompt: fixture.prompt,
        expectedToolCalls: [],
        toolCallSequence: surface,
      };
    }

    const toolCallSequence = surface.filter((entry) =>
      expected.some((exp) => {
        if (exp.tool !== entry.tool) return false;
        if (!exp.scopeMatches) return true;
        if (!entry.scope) return false;
        return (
          minimatch(entry.scope, exp.scopeMatches) ||
          minimatch(exp.scopeMatches, entry.scope)
        );
      })
    );

    return {
      id: fixture.id,
      prompt: fixture.prompt,
      expectedToolCalls: expected,
      toolCallSequence,
    };
  });
}
