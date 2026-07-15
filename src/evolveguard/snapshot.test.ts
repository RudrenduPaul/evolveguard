import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { loadSkill, buildFixtureSnapshots } from './snapshot';
import { EvolveGuardError } from './errors';
import type { CapabilitySurface } from './types';

describe('loadSkill', () => {
  const tmpDir = path.join(
    os.tmpdir(),
    `evolveguard-snapshot-test-${process.pid}-${Date.now()}`
  );

  beforeAll(() => {
    fs.mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('reads, parses, and derives a capability surface for a real file', () => {
    const skillPath = path.join(tmpDir, 'SKILL.md');
    fs.writeFileSync(skillPath, '---\nname: demo\nfilesystem: read-only\n---\nbody');
    const skill = loadSkill(skillPath);
    expect(skill.name).toBe('demo');
    expect(skill.capabilitySurface.map((e) => e.tool)).toContain('fs.read');
  });

  it('throws EvolveGuardError for a missing skill file', () => {
    expect(() => loadSkill(path.join(tmpDir, 'nope.md'))).toThrow(EvolveGuardError);
  });
});

describe('buildFixtureSnapshots', () => {
  const surface: CapabilitySurface = [
    { tool: 'fs.read', source: 'declared', scope: './workspace/**' },
    { tool: 'fs.write', source: 'declared', scope: './workspace/**' },
    {
      tool: 'network.fetch',
      source: 'inferred',
      evidence: [{ file: 'hook.sh', line: 2 }],
    },
  ];

  it('snapshots the full surface when a fixture declares no expectedToolCalls', () => {
    const snapshots = buildFixtureSnapshots(surface, [
      { id: 'a', prompt: 'do everything' },
    ]);
    expect(snapshots[0].toolCallSequence).toEqual(surface);
  });

  it('filters to only the tools a fixture expects', () => {
    const snapshots = buildFixtureSnapshots(surface, [
      { id: 'a', prompt: 'read only', expectedToolCalls: [{ tool: 'fs.read' }] },
    ]);
    expect(snapshots[0].toolCallSequence.map((e) => e.tool)).toEqual(['fs.read']);
  });

  it('respects a scopeMatches constraint on an expected tool call', () => {
    const snapshots = buildFixtureSnapshots(surface, [
      {
        id: 'a',
        prompt: 'scoped',
        expectedToolCalls: [{ tool: 'fs.write', scopeMatches: './workspace/**' }],
      },
    ]);
    expect(snapshots[0].toolCallSequence.map((e) => e.tool)).toEqual(['fs.write']);
  });

  it('excludes a tool whose scope does not satisfy scopeMatches', () => {
    const snapshots = buildFixtureSnapshots(surface, [
      {
        id: 'a',
        prompt: 'scoped',
        expectedToolCalls: [{ tool: 'fs.write', scopeMatches: './other/**' }],
      },
    ]);
    expect(snapshots[0].toolCallSequence).toEqual([]);
  });

  it('excludes a tool with no scope when scopeMatches is required', () => {
    const snapshots = buildFixtureSnapshots(surface, [
      {
        id: 'a',
        prompt: 'scoped',
        expectedToolCalls: [{ tool: 'network.fetch', scopeMatches: './workspace/**' }],
      },
    ]);
    expect(snapshots[0].toolCallSequence).toEqual([]);
  });
});
