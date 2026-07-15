import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { writeBaseline, readBaseline, writeReport, readReport } from './index';
import { EvolveGuardError } from '../errors';
import type { Baseline, EvolveGuardReport } from '../types';

describe('baseline read/write', () => {
  const tmpDir = path.join(
    os.tmpdir(),
    `evolveguard-report-test-${process.pid}-${Date.now()}`
  );

  beforeAll(() => {
    fs.mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  const baseline: Baseline = {
    schemaVersion: 1,
    skillName: 'demo',
    skillPath: '/skills/demo/SKILL.md',
    recordedAt: '2026-07-14T00:00:00.000Z',
    fullCapabilitySurface: [{ tool: 'fs.read', source: 'declared' }],
    fixtures: [
      {
        id: 'f1',
        prompt: 'summarize a PR diff',
        expectedToolCalls: [{ tool: 'fs.read' }],
        toolCallSequence: [{ tool: 'fs.read', source: 'declared' }],
      },
    ],
  };

  it('round-trips a baseline through disk', () => {
    const p = path.join(tmpDir, '.evolveguard-baseline.json');
    writeBaseline(p, baseline);
    const read = readBaseline(p);
    expect(read).toEqual(baseline);
  });

  it('throws EvolveGuardError for a missing baseline file', () => {
    expect(() => readBaseline(path.join(tmpDir, 'nope.json'))).toThrow(EvolveGuardError);
  });

  it('throws EvolveGuardError for invalid JSON', () => {
    const p = path.join(tmpDir, 'bad-baseline.json');
    fs.writeFileSync(p, 'not json');
    expect(() => readBaseline(p)).toThrow(EvolveGuardError);
  });

  it('throws EvolveGuardError for a baseline missing required fields', () => {
    const p = path.join(tmpDir, 'incomplete-baseline.json');
    fs.writeFileSync(p, JSON.stringify({ schemaVersion: 1 }));
    expect(() => readBaseline(p)).toThrow(EvolveGuardError);
  });
});

describe('report read/write', () => {
  const tmpDir = path.join(
    os.tmpdir(),
    `evolveguard-report2-test-${process.pid}-${Date.now()}`
  );

  beforeAll(() => {
    fs.mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  const report: EvolveGuardReport = {
    schemaVersion: 1,
    skillName: 'demo',
    skillPath: '/skills/demo/SKILL.md',
    checkedAt: '2026-07-15T00:00:00.000Z',
    results: [{ id: 'f1', prompt: 'summarize a PR diff', verdict: 'PASS', changes: [] }],
    surfaceChanges: [],
    summary: { pass: 1, drift: 0, total: 1 },
    exitCode: 0,
  };

  it('round-trips a report through disk', () => {
    const p = path.join(tmpDir, 'evolveguard-report.json');
    writeReport(p, report);
    const read = readReport(p);
    expect(read).toEqual(report);
  });

  it('throws EvolveGuardError for a missing report file', () => {
    expect(() => readReport(path.join(tmpDir, 'nope.json'))).toThrow(EvolveGuardError);
  });

  it('throws EvolveGuardError for invalid JSON', () => {
    const p = path.join(tmpDir, 'bad-report.json');
    fs.writeFileSync(p, 'not json');
    expect(() => readReport(p)).toThrow(EvolveGuardError);
  });
});
