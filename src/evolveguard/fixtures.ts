import * as fs from 'node:fs';
import { z } from 'zod';
import type { Fixture } from './types';
import { EvolveGuardError } from './errors';

const expectedToolCallSchema = z.object({
  tool: z.string().min(1),
  scopeMatches: z.string().optional(),
});

const fixtureSchema = z.object({
  id: z.string().min(1),
  prompt: z.string().min(1),
  expectedToolCalls: z.array(expectedToolCallSchema).optional(),
});

const fixturesFileSchema = z.array(fixtureSchema).min(1);

/** Reads and validates a user-supplied fixtures.json against the documented schema. */
export function loadFixtures(fixturesPath: string): Fixture[] {
  let raw: string;
  try {
    raw = fs.readFileSync(fixturesPath, 'utf8');
  } catch (err) {
    throw new EvolveGuardError(
      `Could not read fixtures file at "${fixturesPath}".`,
      err instanceof Error ? err.message : String(err),
      'Pass a valid path to a fixtures JSON file with --fixtures.'
    );
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new EvolveGuardError(
      `Fixtures file at "${fixturesPath}" is not valid JSON.`,
      err instanceof Error ? err.message : String(err),
      'Fix the JSON syntax, e.g. run it through `node -e "JSON.parse(require(\'fs\').readFileSync(process.argv[1]))"`.'
    );
  }

  const result = fixturesFileSchema.safeParse(parsed);
  if (!result.success) {
    throw new EvolveGuardError(
      `Fixtures file at "${fixturesPath}" does not match the expected schema.`,
      result.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).join('; '),
      'A fixtures file is a non-empty JSON array of {"id": string, "prompt": string, "expectedToolCalls"?: [{"tool": string, "scopeMatches"?: string}]}.'
    );
  }

  const ids = new Set<string>();
  for (const fixture of result.data) {
    if (ids.has(fixture.id)) {
      throw new EvolveGuardError(
        `Duplicate fixture id "${fixture.id}" in "${fixturesPath}".`,
        'Fixture ids must be unique within a fixtures file -- they are used to match baseline entries on replay.',
        'Give each fixture a unique id.'
      );
    }
    ids.add(fixture.id);
  }

  return result.data;
}
