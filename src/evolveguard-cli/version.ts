import * as fs from 'node:fs';
import * as path from 'node:path';

/**
 * Reads the CLI's own version from package.json at runtime, relative to this
 * module's location, instead of a hardcoded string.
 *
 * A hardcoded VERSION constant silently drifts from the version actually
 * published to npm/PyPI every time a release bumps package.json without
 * remembering to update the constant too (this happened across the 0.1.1,
 * 0.1.2, and 0.1.3 releases: `evolveguard --version` and every human-readable
 * command header kept printing "0.1.0"). Reading it from package.json makes
 * that class of drift impossible going forward.
 */
export function getVersion(): string {
  try {
    const pkgPath = path.join(__dirname, '..', '..', 'package.json');
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8')) as { version?: string };
    return pkg.version ?? '0.0.0';
  } catch {
    return '0.0.0';
  }
}
