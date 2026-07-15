/** Shared WHAT/WHY/FIX error formatting, matching the founders' other CLI tools in this portfolio. */
export function formatWhatWhyFix(what: string, why: string, fix: string): string {
  return `WHAT: ${what}\nWHY:  ${why}\nFIX:  ${fix}`;
}

export class EvolveGuardError extends Error {
  constructor(
    public readonly what: string,
    public readonly why: string,
    public readonly fix: string
  ) {
    super(formatWhatWhyFix(what, why, fix));
    this.name = 'EvolveGuardError';
  }
}
