import * as fs from 'node:fs';
import * as path from 'node:path';
import { EvolveGuardError } from './errors';

function escapesBase(resolvedBase: string, resolvedTarget: string): boolean {
  const relative = path.relative(resolvedBase, resolvedTarget);
  return relative.startsWith('..') || path.isAbsolute(relative);
}

function outsideBaseError(userPath: string, resolvedBase: string): EvolveGuardError {
  return new EvolveGuardError(
    `Path "${userPath}" resolves outside its skill directory.`,
    `Hook and reference paths declared in a skill file must stay within the skill's own directory (${resolvedBase}) -- this prevents a malicious or accidentally-broken skill file from making EvolveGuard read files outside its scope.`,
    'Use a path relative to the skill file that stays inside its own directory, and make sure it is not a symlink pointing elsewhere.'
  );
}

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
 *
 * The lexical check alone is not enough: a path that looks safe
 * ("hooks/pre.sh") can itself be a symlink whose real target lives outside
 * the skill directory, and fs.readFileSync follows symlinks transparently.
 * So after the lexical check passes, this also resolves symlinks (via
 * fs.realpathSync) on both the base and the target and re-checks the same
 * containment invariant against the real paths -- a symlink escape fails
 * exactly like a literal "../" escape. A target that does not exist yet
 * (e.g. a hook path being validated before the file is created) skips the
 * realpath re-check rather than erroring on ENOENT; the caller's own
 * fs.readFileSync will fail on it as before.
 */
export function resolveWithinBase(baseDir: string, userPath: string): string {
  const resolvedBase = path.resolve(baseDir);
  const resolvedTarget = path.resolve(resolvedBase, userPath);

  if (escapesBase(resolvedBase, resolvedTarget)) {
    throw outsideBaseError(userPath, resolvedBase);
  }

  let realBase: string;
  let realTarget: string;
  try {
    realBase = fs.realpathSync(resolvedBase);
    realTarget = fs.realpathSync(resolvedTarget);
  } catch {
    // Base or target doesn't exist on disk (yet) -- nothing to follow, the
    // lexical check above already stands as the answer for this call.
    return resolvedTarget;
  }

  if (escapesBase(realBase, realTarget)) {
    throw outsideBaseError(userPath, resolvedBase);
  }

  return resolvedTarget;
}

/** Resolves and validates a top-level CLI-supplied path (SKILL.md, fixtures.json, baseline, report). */
export function resolveCliPath(cwd: string, userPath: string): string {
  return path.resolve(cwd, userPath);
}
