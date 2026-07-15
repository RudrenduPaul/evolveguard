import * as path from 'node:path';
import { EvolveGuardError } from './errors';

/**
 * Resolves a user-supplied path (SKILL.md, fixtures.json, a hook script
 * referenced from frontmatter) and rejects anything that escapes the
 * expected base directory. This is the one place path-traversal protection
 * lives -- every module that reads a file supplied indirectly through
 * frontmatter (hook script paths) routes through this function rather than
 * concatenating strings and calling fs.readFileSync directly.
 *
 * A skill file's own frontmatter is untrusted input (it may itself be the
 * edit under test), so `hooks: ["../../../etc/passwd"]` must never resolve
 * outside the skill's own directory.
 */
export function resolveWithinBase(baseDir: string, userPath: string): string {
  const resolvedBase = path.resolve(baseDir);
  const resolvedTarget = path.resolve(resolvedBase, userPath);
  const relative = path.relative(resolvedBase, resolvedTarget);

  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new EvolveGuardError(
      `Path "${userPath}" resolves outside its skill directory.`,
      `Hook and reference paths declared in a skill file must stay within the skill's own directory (${resolvedBase}) -- this prevents a malicious or accidentally-broken skill file from making EvolveGuard read files outside its scope.`,
      'Use a path relative to the skill file that stays inside its own directory.'
    );
  }

  return resolvedTarget;
}

/** Resolves and validates a top-level CLI-supplied path (SKILL.md, fixtures.json, baseline, report). */
export function resolveCliPath(cwd: string, userPath: string): string {
  return path.resolve(cwd, userPath);
}
