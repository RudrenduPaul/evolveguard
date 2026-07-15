import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { recordBaseline } from '../record/index';
import { replaySkill } from './index';

describe('replaySkill', () => {
  const tmpDir = path.join(
    os.tmpdir(),
    `evolveguard-replay-test-${process.pid}-${Date.now()}`
  );
  const skillPath = path.join(tmpDir, 'SKILL.md');
  const fixturesPath = path.join(tmpDir, 'fixtures.json');

  beforeAll(() => {
    fs.mkdirSync(tmpDir, { recursive: true });
    fs.writeFileSync(skillPath, '---\nname: demo\nfilesystem: read-only\n---\nbody');
    fs.writeFileSync(
      fixturesPath,
      JSON.stringify([
        { id: 'f1', prompt: 'read a file', expectedToolCalls: [{ tool: 'fs.read' }] },
      ])
    );
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('reproduces the same tool-call sequence when the skill is unchanged', () => {
    const baseline = recordBaseline(skillPath, fixturesPath);
    const replay = replaySkill(skillPath, baseline);
    expect(replay.fixtures[0].toolCallSequence.map((e) => e.tool)).toEqual(
      baseline.fixtures[0].toolCallSequence.map((e) => e.tool)
    );
  });

  it('picks up a new capability after the skill file is edited', () => {
    const baseline = recordBaseline(skillPath, fixturesPath);
    fs.writeFileSync(skillPath, '---\nname: demo\nfilesystem: read-write\n---\nbody');

    // The baseline fixture only expected fs.read, so re-snapshotting against
    // the edited (now read-write) surface still yields fs.read for this
    // fixture -- fs.write only shows up in fixtures that expect it, or in
    // fullCapabilitySurface, which is exactly what diff/ is responsible for
    // comparing at the whole-surface level.
    const replay = replaySkill(skillPath, baseline);
    expect(replay.fullCapabilitySurface.map((e) => e.tool)).toContain('fs.write');
  });
});
