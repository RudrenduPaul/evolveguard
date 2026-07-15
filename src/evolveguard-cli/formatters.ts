import type { Baseline, EvolveGuardReport } from '../evolveguard/types';

const VERSION = '0.1.0';

export function formatRecordResult(baseline: Baseline, baselinePath: string): string {
  const lines: string[] = [];
  lines.push(`EvolveGuard v${VERSION} -- Baseline Recorded`);
  lines.push(`skill: ${baseline.skillName}  fixtures: ${baseline.fixtures.length}`);
  lines.push('');
  for (const fixture of baseline.fixtures) {
    const toolNames =
      fixture.toolCallSequence.map((e) => e.tool).join(', ') ||
      '(no capabilities detected)';
    lines.push(`  recorded  fixture: "${fixture.prompt}"  tools: ${toolNames}`);
  }
  lines.push('');
  lines.push(`baseline written to ${baselinePath}`);
  return lines.join('\n');
}

export function formatCheckResult(
  report: EvolveGuardReport,
  baselineRecordedAt: string
): string {
  const lines: string[] = [];
  const date = baselineRecordedAt.slice(0, 10);
  lines.push(`EvolveGuard v${VERSION} -- Regression Check`);
  lines.push(
    `skill: ${report.skillName}  baseline: ${date}  fixtures: ${report.summary.total}`
  );
  lines.push('');

  for (const result of report.results) {
    const tag = result.verdict === 'PASS' ? '[PASS] ' : '[DRIFT]';
    if (result.verdict === 'PASS') {
      lines.push(`${tag} fixture: "${result.prompt}"  tool-call sequence unchanged`);
    } else {
      const first = result.changes[0];
      lines.push(
        `${tag} fixture: "${result.prompt}"  ${first ? summarizeChange(first) : 'behavior changed'}`
      );
      for (const change of result.changes) {
        lines.push(`         -> ${change.message}`);
      }
    }
  }

  if (report.surfaceChanges.length > 0) {
    lines.push('');
    lines.push('skill-level surface changes (not tied to a specific fixture):');
    for (const change of report.surfaceChanges) {
      lines.push(`  -> ${change.message}`);
    }
  }

  lines.push('');
  lines.push(`${report.summary.pass} PASS, ${report.summary.drift} DRIFT, 0 FAIL`);
  if (report.exitCode === 1) {
    lines.push(
      'exit code 1 (DRIFT blocks merge by default; override with --allow-drift)'
    );
  } else {
    lines.push('exit code 0');
  }

  return lines.join('\n');
}

function summarizeChange(
  change: EvolveGuardReport['results'][number]['changes'][number]
): string {
  if (change.kind === 'added') return `new tool call: ${change.tool} (baseline had none)`;
  if (change.kind === 'removed') return `tool call removed: ${change.tool}`;
  return `scope changed: ${change.tool}`;
}

export function formatReport(report: EvolveGuardReport): string {
  const lines: string[] = [];
  lines.push(`EvolveGuard v${VERSION} -- Report`);
  lines.push(`skill: ${report.skillName}  checked: ${report.checkedAt}`);
  lines.push('');
  for (const result of report.results) {
    lines.push(`[${result.verdict}] ${result.id}: ${result.prompt}`);
    for (const change of result.changes) {
      lines.push(`  -> ${change.message}`);
    }
  }
  if (report.surfaceChanges.length > 0) {
    lines.push('');
    lines.push('skill-level surface changes:');
    for (const change of report.surfaceChanges) {
      lines.push(`  -> ${change.message}`);
    }
  }
  lines.push('');
  lines.push(`${report.summary.pass} PASS, ${report.summary.drift} DRIFT, 0 FAIL`);
  lines.push(`exit code ${report.exitCode}`);
  return lines.join('\n');
}
