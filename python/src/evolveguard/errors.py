"""
Shared WHAT/WHY/FIX error formatting for EvolveGuardError messages. Ported
verbatim from src/evolveguard/errors.ts.
"""
from __future__ import annotations


def format_what_why_fix(what: str, why: str, fix: str) -> str:
    return f"WHAT: {what}\nWHY:  {why}\nFIX:  {fix}"


class EvolveGuardError(Exception):
    def __init__(self, what: str, why: str, fix: str) -> None:
        super().__init__(format_what_why_fix(what, why, fix))
        self.what = what
        self.why = why
        self.fix = fix
