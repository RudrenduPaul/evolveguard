import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { recordBaseline } from './index';

describe('recordBaseline', () => {
  const tmpDir = path.join(
    os.tmpdir(),
    `evolveguard-record-test-${process.pid}-${Date.now()}`
  );

  beforeAll(() => {
    fs.mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('records a baseline with per-fixture tool-call sequences', () => {
    const skillPath = path.join(tmpDir, 'SKILL.md');
    fs.writeFileSync(
      skillPath,
      '---\nname: demo\nfilesystem: read-only\nscope: "./workspace/**"\n---\nbody'
    );

    const fixturesPath = path.join(tmpDir, 'fixtures.json');
    fs.writeFileSync(
      fixturesPath,
      JSON.stringify([
        {
          id: 'read-fixture',
          prompt: 'summarize a PR diff',
          expectedToolCalls: [{ tool: 'fs.read' }],
        },
      ])
    );

    const baseline = recordBaseline(skillPath, fixturesPath);

    expect(baseline.skillName).toBe('demo');
    expect(baseline.fixtures).toHaveLength(1);
    expect(baseline.fixtures[0].toolCallSequence.map((e) => e.tool)).toEqual(['fs.read']);
    expect(baseline.fullCapabilitySurface.map((e) => e.tool)).toContain('fs.read');
    expect(new Date(baseline.recordedAt).toString()).not.toBe('Invalid Date');
  });
});
