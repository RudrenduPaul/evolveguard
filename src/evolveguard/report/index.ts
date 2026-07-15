import * as fs from 'node:fs';
import { z } from 'zod';
import type { Baseline, EvolveGuardReport } from '../types';
import { EvolveGuardError } from '../errors';

const capabilityEntrySchema = z.object({
  tool: z.string(),
  source: z.enum(['declared', 'inferred']),
  scope: z.string().optional(),
  evidence: z.array(z.object({ file: z.string(), line: z.number() })).optional(),
});

const fixtureSnapshotSchema = z.object({
  id: z.string(),
  prompt: z.string(),
  expectedToolCalls: z.array(
    z.object({ tool: z.string(), scopeMatches: z.string().optional() })
  ),
  toolCallSequence: z.array(capabilityEntrySchema),
});

const baselineSchema = z.object({
  schemaVersion: z.literal(1),
  skillName: z.string(),
  skillPath: z.string(),
  recordedAt: z.string(),
  fullCapabilitySurface: z.array(capabilityEntrySchema),
  fixtures: z.array(fixtureSnapshotSchema).min(1),
});

/** Writes a recorded baseline to disk as pretty-printed, deterministic JSON. */
export function writeBaseline(baselinePath: string, baseline: Baseline): void {
  fs.writeFileSync(baselinePath, JSON.stringify(baseline, null, 2) + '\n', 'utf8');
}

/** Reads and validates a baseline file written by `evolveguard record`. */
export function readBaseline(baselinePath: string): Baseline {
  let raw: string;
  try {
    raw = fs.readFileSync(baselinePath, 'utf8');
  } catch (err) {
    throw new EvolveGuardError(
      `Could not read baseline file at "${baselinePath}".`,
      err instanceof Error ? err.message : String(err),
      'Run `evolveguard record <SKILL.md> --fixtures <fixtures.json>` first to create a baseline.'
    );
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new EvolveGuardError(
      `Baseline file at "${baselinePath}" is not valid JSON.`,
      err instanceof Error ? err.message : String(err),
      'Re-run `evolveguard record` to regenerate the baseline file.'
    );
  }

  const result = baselineSchema.safeParse(parsed);
  if (!result.success) {
    throw new EvolveGuardError(
      `Baseline file at "${baselinePath}" does not match the expected schema.`,
      result.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).join('; '),
      'Re-run `evolveguard record` to regenerate the baseline file, or check it was not hand-edited.'
    );
  }

  return result.data;
}

/** Writes a check report to disk as pretty-printed JSON. */
export function writeReport(reportPath: string, report: EvolveGuardReport): void {
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n', 'utf8');
}

const capabilityChangeSchema = z.object({
  kind: z.enum(['added', 'removed', 'scope-widened', 'scope-changed']),
  tool: z.string(),
  baselineScope: z.string().optional(),
  newScope: z.string().optional(),
  message: z.string(),
});

const reportSchema = z.object({
  schemaVersion: z.literal(1),
  skillName: z.string(),
  skillPath: z.string(),
  checkedAt: z.string(),
  results: z.array(
    z.object({
      id: z.string(),
      prompt: z.string(),
      verdict: z.enum(['PASS', 'DRIFT']),
      changes: z.array(capabilityChangeSchema),
    })
  ),
  surfaceChanges: z.array(capabilityChangeSchema),
  summary: z.object({ pass: z.number(), drift: z.number(), total: z.number() }),
  exitCode: z.union([z.literal(0), z.literal(1), z.literal(2)]),
});

/** Reads and validates a report file written by `evolveguard check`. */
export function readReport(reportPath: string): EvolveGuardReport {
  let raw: string;
  try {
    raw = fs.readFileSync(reportPath, 'utf8');
  } catch (err) {
    throw new EvolveGuardError(
      `Could not read report file at "${reportPath}".`,
      err instanceof Error ? err.message : String(err),
      'Run `evolveguard check <SKILL.md>` first to generate a report.'
    );
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new EvolveGuardError(
      `Report file at "${reportPath}" is not valid JSON.`,
      err instanceof Error ? err.message : String(err),
      'Re-run `evolveguard check` to regenerate the report file.'
    );
  }

  const result = reportSchema.safeParse(parsed);
  if (!result.success) {
    throw new EvolveGuardError(
      `Report file at "${reportPath}" does not match the expected schema.`,
      result.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).join('; '),
      'Re-run `evolveguard check` to regenerate the report file.'
    );
  }

  return result.data;
}
