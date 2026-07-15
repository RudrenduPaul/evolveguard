import { describe, it, expect } from 'vitest';
import { resolveWithinBase, resolveCliPath } from './paths';
import { EvolveGuardError } from './errors';
import * as path from 'node:path';

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
});

describe('resolveCliPath', () => {
  it('resolves a relative path against the given cwd', () => {
    expect(resolveCliPath('/a/b', 'c.json')).toBe(path.resolve('/a/b/c.json'));
  });
});
