"""
Resolves a user-supplied path (SKILL.md, fixtures.json, a hook script
referenced from frontmatter) and rejects anything that escapes the
expected base directory. This is the one place path-traversal protection
lives -- every module that reads a file supplied indirectly through
frontmatter (hook script paths) routes through this function rather than
concatenating strings and calling open() directly.

A skill file's own frontmatter is untrusted input (it may itself be the
edit under test), so `hooks: ["../../../etc/passwd"]` must never resolve
outside the skill's own directory.

The lexical check alone is not enough: a path that looks safe
("hooks/pre.sh") can itself be a symlink whose real target lives outside
the skill directory, and open() follows symlinks transparently. So after
the lexical check passes, this also resolves symlinks (via
os.path.realpath) on both the base and the target and re-checks the same
containment invariant against the real paths -- a symlink escape fails
exactly like a literal "../" escape. A target that does not exist yet
(e.g. a hook path being validated before the file is created) skips the
realpath re-check rather than erroring; the caller's own file read will
fail on it as before.

Ported from src/evolveguard/paths.ts.
"""
from __future__ import annotations

import os

from .errors import EvolveGuardError


def _resolve(base: str, target: str) -> str:
    combined = target if os.path.isabs(target) else os.path.join(base, target)
    return os.path.normpath(combined)


def _escapes_base(resolved_base: str, resolved_target: str) -> bool:
    relative = os.path.relpath(resolved_target, resolved_base)
    return relative == ".." or relative.startswith(".." + os.sep)


def _outside_base_error(user_path: str, resolved_base: str) -> EvolveGuardError:
    return EvolveGuardError(
        f'Path "{user_path}" resolves outside its skill directory.',
        f"Hook and reference paths declared in a skill file must stay within "
        f"the skill's own directory ({resolved_base}) -- this prevents a "
        f"malicious or accidentally-broken skill file from making EvolveGuard "
        f"read files outside its scope.",
        "Use a path relative to the skill file that stays inside its own "
        "directory, and make sure it is not a symlink pointing elsewhere.",
    )


def resolve_within_base(base_dir: str, user_path: str) -> str:
    resolved_base = os.path.abspath(base_dir)
    resolved_target = _resolve(resolved_base, user_path)

    if _escapes_base(resolved_base, resolved_target):
        raise _outside_base_error(user_path, resolved_base)

    if not os.path.exists(resolved_base) or not os.path.exists(resolved_target):
        # Base or target doesn't exist on disk (yet) -- nothing to follow, the
        # lexical check above already stands as the answer for this call.
        return resolved_target

    real_base = os.path.realpath(resolved_base)
    real_target = os.path.realpath(resolved_target)

    if _escapes_base(real_base, real_target):
        raise _outside_base_error(user_path, resolved_base)

    return resolved_target


def resolve_cli_path(cwd: str, user_path: str) -> str:
    """Resolves and validates a top-level CLI-supplied path (SKILL.md, fixtures.json, baseline, report)."""
    return _resolve(os.path.abspath(cwd), user_path)
