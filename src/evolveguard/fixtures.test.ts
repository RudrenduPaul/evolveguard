import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { loadFixtures } from './fixtures';
import { EvolveGuardError } from './errors';

describe('loadFixtures', () => {
  const tmpDir = path.join(
    os.tmpdir(),
    `evolveguard-fixtures-test-${process.pid}-${Date.now()}`
  );

  beforeAll(() => {
    fs.mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  function write(name: string, content: string): string {
    const p = path.join(tmpDir, name);
    fs.writeFileSync(p, content, 'utf8');
    return p;
  }

  it('loads a well-formed fixtures file', () => {
    const p = write(
      'good.json',
      JSON.stringify([
        { id: 'a', prompt: 'do a thing', expectedToolCalls: [{ tool: 'fs.read' }] },
      ])
    );
    const fixtures = loadFixtures(p);
    expect(fixtures).toHaveLength(1);
    expect(fixtures[0].id).toBe('a');
  });

  it('allows expectedToolCalls to be omitted', () => {
    const p = write('minimal.json', JSON.stringify([{ id: 'a', prompt: 'do a thing' }]));
    const fixtures = loadFixtures(p);
    expect(fixtures[0].expectedToolCalls).toBeUndefined();
  });

  it('throws EvolveGuardError for a missing file', () => {
    expect(() => loadFixtures(path.join(tmpDir, 'nope.json'))).toThrow(EvolveGuardError);
  });

  it('throws EvolveGuardError for invalid JSON', () => {
    const p = write('bad.json', '{not json');
    expect(() => loadFixtures(p)).toThrow(EvolveGuardError);
  });

  it('throws EvolveGuardError for an empty array', () => {
    const p = write('empty.json', '[]');
    expect(() => loadFixtures(p)).toThrow(EvolveGuardError);
  });

  it('throws EvolveGuardError for a fixture missing a required field', () => {
    const p = write('missing-field.json', JSON.stringify([{ id: 'a' }]));
    expect(() => loadFixtures(p)).toThrow(EvolveGuardError);
  });

  it('throws EvolveGuardError for duplicate fixture ids', () => {
    const p = write(
      'dupes.json',
      JSON.stringify([
        { id: 'a', prompt: 'one' },
        { id: 'a', prompt: 'two' },
      ])
    );
    expect(() => loadFixtures(p)).toThrow(EvolveGuardError);
  });
});
