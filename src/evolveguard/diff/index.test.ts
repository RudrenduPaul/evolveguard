import { describe, it, expect } from 'vitest';
import { diffFixture, diffSurface, diffAll } from './index';
import type { Baseline, FixtureSnapshot, ReplayResult } from '../types';

function fixture(
  id: string,
  prompt: string,
  tools: { tool: string; scope?: string }[]
): FixtureSnapshot {
  return {
    id,
    prompt,
    expectedToolCalls: tools.map((t) => ({ tool: t.tool })),
    toolCallSequence: tools.map((t) => ({
      tool: t.tool,
      source: 'declared',
      scope: t.scope,
    })),
  };
}

describe('diffFixture', () => {
  it('returns PASS when the tool-call sequence is unchanged', () => {
    const baseline = fixture('f1', 'summarize a PR diff', [{ tool: 'fs.read' }]);
    const replayed = fixture('f1', 'summarize a PR diff', [{ tool: 'fs.read' }]);
    const result = diffFixture(baseline, replayed);
    expect(result.verdict).toBe('PASS');
    expect(result.changes).toEqual([]);
  });

  it('flags DRIFT when a new tool call appears', () => {
    const baseline = fixture('f2', 'scan a monorepo', [{ tool: 'fs.read' }]);
    const replayed = fixture('f2', 'scan a monorepo', [
      { tool: 'fs.read' },
      { tool: 'fs.write' },
    ]);
    const result = diffFixture(baseline, replayed);
    expect(result.verdict).toBe('DRIFT');
    expect(result.changes).toHaveLength(1);
    expect(result.changes[0].kind).toBe('added');
    expect(result.changes[0].tool).toBe('fs.write');
    expect(result.changes[0].message).toContain('new tool call: fs.write');
  });

  it('flags DRIFT when a tool call disappears', () => {
    const baseline = fixture('f3', 'flag a secrets leak', [
      { tool: 'fs.read' },
      { tool: 'fs.write' },
    ]);
    const replayed = fixture('f3', 'flag a secrets leak', [{ tool: 'fs.read' }]);
    const result = diffFixture(baseline, replayed);
    expect(result.verdict).toBe('DRIFT');
    expect(result.changes[0].kind).toBe('removed');
  });

  it('flags DRIFT when a scope changes for the same tool', () => {
    const baseline = fixture('f4', 'write to workspace', [
      { tool: 'fs.write', scope: './workspace/**' },
    ]);
    const replayed = fixture('f4', 'write to workspace', [
      { tool: 'fs.write', scope: './**' },
    ]);
    const result = diffFixture(baseline, replayed);
    expect(result.verdict).toBe('DRIFT');
    expect(result.changes[0].kind).toBe('scope-changed');
    expect(result.changes[0].message).toContain('./workspace/**');
    expect(result.changes[0].message).toContain('./**');
  });
});

describe('diffSurface', () => {
  it('returns no changes for an identical surface', () => {
    const surface = [{ tool: 'fs.read', source: 'declared' as const }];
    expect(diffSurface(surface, surface)).toEqual([]);
  });

  it('flags a capability that appears in the replay but not the baseline', () => {
    const baseline = [{ tool: 'fs.read', source: 'declared' as const }];
    const replay = [
      { tool: 'fs.read', source: 'declared' as const },
      { tool: 'exec.shell', source: 'inferred' as const },
    ];
    const changes = diffSurface(baseline, replay);
    expect(changes).toHaveLength(1);
    expect(changes[0].kind).toBe('added');
    expect(changes[0].tool).toBe('exec.shell');
  });
});

describe('diffAll', () => {
  function makeBaseline(): Baseline {
    return {
      schemaVersion: 1,
      skillName: 'demo',
      skillPath: '/skills/demo/SKILL.md',
      recordedAt: '2026-07-14T00:00:00.000Z',
      fullCapabilitySurface: [{ tool: 'fs.read', source: 'declared' }],
      fixtures: [fixture('f1', 'summarize a PR diff', [{ tool: 'fs.read' }])],
    };
  }

  it('reports all PASS and exit code 0 when nothing changed', () => {
    const baseline = makeBaseline();
    const replay: ReplayResult = {
      schemaVersion: 1,
      skillName: 'demo',
      skillPath: '/skills/demo/SKILL.md',
      replayedAt: '2026-07-15T00:00:00.000Z',
      fullCapabilitySurface: [{ tool: 'fs.read', source: 'declared' }],
      fixtures: [fixture('f1', 'summarize a PR diff', [{ tool: 'fs.read' }])],
    };
    const report = diffAll(baseline, replay);
    expect(report.summary).toEqual({ pass: 1, drift: 0, total: 1 });
    expect(report.exitCode).toBe(0);
  });

  it('reports DRIFT and exit code 1 when a fixture gains a new tool call', () => {
    const baseline = makeBaseline();
    const replay: ReplayResult = {
      schemaVersion: 1,
      skillName: 'demo',
      skillPath: '/skills/demo/SKILL.md',
      replayedAt: '2026-07-15T00:00:00.000Z',
      fullCapabilitySurface: [
        { tool: 'fs.read', source: 'declared' },
        { tool: 'fs.write', source: 'declared' },
      ],
      fixtures: [
        fixture('f1', 'summarize a PR diff', [{ tool: 'fs.read' }, { tool: 'fs.write' }]),
      ],
    };
    const report = diffAll(baseline, replay);
    expect(report.summary).toEqual({ pass: 0, drift: 1, total: 1 });
    expect(report.exitCode).toBe(1);
  });

  it('exit code stays 0 with --allow-drift even when drift is detected', () => {
    const baseline = makeBaseline();
    const replay: ReplayResult = {
      schemaVersion: 1,
      skillName: 'demo',
      skillPath: '/skills/demo/SKILL.md',
      replayedAt: '2026-07-15T00:00:00.000Z',
      fullCapabilitySurface: [
        { tool: 'fs.read', source: 'declared' },
        { tool: 'fs.write', source: 'declared' },
      ],
      fixtures: [
        fixture('f1', 'summarize a PR diff', [{ tool: 'fs.read' }, { tool: 'fs.write' }]),
      ],
    };
    const report = diffAll(baseline, replay, { allowDrift: true });
    expect(report.summary.drift).toBe(1);
    expect(report.exitCode).toBe(0);
  });

  it('flags DRIFT with exit code 1 for a surface-level change no fixture expected', () => {
    const baseline = makeBaseline();
    const replay: ReplayResult = {
      schemaVersion: 1,
      skillName: 'demo',
      skillPath: '/skills/demo/SKILL.md',
      replayedAt: '2026-07-15T00:00:00.000Z',
      fullCapabilitySurface: [
        { tool: 'fs.read', source: 'declared' },
        { tool: 'exec.shell', source: 'inferred' },
      ],
      fixtures: [fixture('f1', 'summarize a PR diff', [{ tool: 'fs.read' }])],
    };
    const report = diffAll(baseline, replay);
    expect(report.summary).toEqual({ pass: 1, drift: 0, total: 1 });
    expect(report.surfaceChanges).toHaveLength(1);
    expect(report.exitCode).toBe(1);
  });

  it('flags DRIFT when a fixture from the baseline is missing from the replay', () => {
    const baseline = makeBaseline();
    const replay: ReplayResult = {
      schemaVersion: 1,
      skillName: 'demo',
      skillPath: '/skills/demo/SKILL.md',
      replayedAt: '2026-07-15T00:00:00.000Z',
      fullCapabilitySurface: [{ tool: 'fs.read', source: 'declared' }],
      fixtures: [],
    };
    const report = diffAll(baseline, replay);
    expect(report.results[0].verdict).toBe('DRIFT');
    expect(report.exitCode).toBe(1);
  });
});
