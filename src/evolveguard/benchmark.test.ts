import { describe, it, expect } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { recordBaseline } from './record/index';
import { replaySkill } from './replay/index';
import { diffAll } from './diff/index';

/**
 * Runs EvolveGuard's own record -> replay -> diff pipeline against the
 * labeled corpus in fixtures/labeled-non-breaking-edits/ and reports the
 * false-positive rate: how often a case labeled "non-breaking" is
 * classified as DRIFT (a fixture-level DRIFT or a surface-level change).
 *
 * Benchmark command this number comes from:
 *   npx vitest run src/evolveguard/benchmark.test.ts
 *
 * This number must never be stated in the README without this exact
 * command reproducing it -- no claiming a benchmark result without a
 * runnable, reviewable way to reproduce it.
 */

const CORPUS_DIR = path.resolve(__dirname, '../../fixtures/labeled-non-breaking-edits');

interface Label {
  classification: 'non-breaking' | 'breaking';
  reason: string;
}

function listCases(): string[] {
  return fs
    .readdirSync(CORPUS_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}

function runCase(caseName: string): { hasDrift: boolean } {
  const caseDir = path.join(CORPUS_DIR, caseName);
  const beforePath = path.join(caseDir, 'before', 'SKILL.md');
  const afterPath = path.join(caseDir, 'after', 'SKILL.md');
  const fixturesPath = path.join(caseDir, 'fixtures.json');

  const baseline = recordBaseline(beforePath, fixturesPath);
  const replay = replaySkill(afterPath, baseline);
  const report = diffAll(baseline, replay);

  const hasDrift = report.summary.drift > 0 || report.surfaceChanges.length > 0;
  return { hasDrift };
}

describe('false-positive rate benchmark (fixtures/labeled-non-breaking-edits)', () => {
  const cases = listCases();

  it('finds at least one non-breaking and one breaking case in the corpus', () => {
    expect(cases.length).toBeGreaterThanOrEqual(4);
  });

  for (const caseName of cases) {
    it(`classifies ${caseName} per its label`, () => {
      const label: Label = JSON.parse(
        fs.readFileSync(path.join(CORPUS_DIR, caseName, 'label.json'), 'utf8')
      );
      const { hasDrift } = runCase(caseName);

      if (label.classification === 'non-breaking') {
        expect(
          hasDrift,
          `${caseName} is labeled non-breaking but EvolveGuard flagged drift`
        ).toBe(false);
      } else {
        expect(
          hasDrift,
          `${caseName} is labeled breaking but EvolveGuard found no drift`
        ).toBe(true);
      }
    });
  }

  it('reports a 0% false-positive rate across the whole corpus', () => {
    const nonBreakingCases = cases.filter((caseName) => {
      const label: Label = JSON.parse(
        fs.readFileSync(path.join(CORPUS_DIR, caseName, 'label.json'), 'utf8')
      );
      return label.classification === 'non-breaking';
    });

    const falsePositives = nonBreakingCases.filter(
      (caseName) => runCase(caseName).hasDrift
    );
    const falsePositiveRate =
      nonBreakingCases.length > 0 ? falsePositives.length / nonBreakingCases.length : 0;

    expect(falsePositiveRate).toBe(0);
  });
});
