#!/usr/bin/env node
import { Command } from 'commander';
import * as path from 'node:path';
import { recordBaseline } from '../evolveguard/record/index';
import { replaySkill } from '../evolveguard/replay/index';
import { diffAll } from '../evolveguard/diff/index';
import {
  writeBaseline,
  readBaseline,
  writeReport,
  readReport,
} from '../evolveguard/report/index';
import { EvolveGuardError, formatWhatWhyFix } from '../evolveguard/errors';
import { formatRecordResult, formatCheckResult, formatReport } from './formatters';

const VERSION = '0.1.0';
const DEFAULT_REPORT_PATH = './evolveguard-report.json';

function defaultBaselinePath(skillPath: string): string {
  return path.join(path.dirname(path.resolve(skillPath)), '.evolveguard-baseline.json');
}

export async function runCli(argv: string[]): Promise<number> {
  const program = new Command();
  program
    .name('evolveguard')
    .description(
      "Regression-testing CLI for self-edited Claude Agent Skills (SKILL.md, MEMORY.md) -- golden-transcript record/replay against a skill's own declared and inferred capability surface, zero hosted infrastructure."
    )
    .version(VERSION)
    .exitOverride();

  let exitCode = 0;

  program
    .command('record')
    .description(
      'Record a golden-transcript baseline for a skill against a set of labeled fixtures'
    )
    .argument('<skillPath>', 'path to the SKILL.md or MEMORY.md file to baseline')
    .requiredOption(
      '--fixtures <path>',
      'path to a fixtures JSON file (array of {id, prompt, expectedToolCalls?})'
    )
    .option(
      '--baseline <path>',
      'path to write the baseline file (default: <skill-dir>/.evolveguard-baseline.json)'
    )
    .option('--json', 'output structured JSON instead of human-readable text', false)
    .action(
      (
        skillPath: string,
        opts: { fixtures: string; baseline?: string; json: boolean }
      ) => {
        try {
          const baseline = recordBaseline(skillPath, opts.fixtures);
          const baselinePath = opts.baseline ?? defaultBaselinePath(skillPath);
          writeBaseline(baselinePath, baseline);

          if (opts.json) {
            process.stdout.write(
              JSON.stringify({ baseline, baselinePath }, null, 2) + '\n'
            );
          } else {
            process.stdout.write(formatRecordResult(baseline, baselinePath) + '\n');
          }
          exitCode = 0;
        } catch (err) {
          exitCode = handleError(err);
        }
      }
    );

  program
    .command('check')
    .description(
      'Replay the fixtures from a baseline against the current (possibly edited) skill and report drift'
    )
    .argument('<skillPath>', 'path to the SKILL.md or MEMORY.md file to check')
    .option(
      '--baseline <path>',
      'path to the baseline file (default: <skill-dir>/.evolveguard-baseline.json)'
    )
    .option('--report <path>', 'path to write the report file', DEFAULT_REPORT_PATH)
    .option(
      '--allow-drift',
      'exit 0 even if drift is detected (drift is still reported)',
      false
    )
    .option('--json', 'output structured JSON instead of human-readable text', false)
    .action(
      (
        skillPath: string,
        opts: { baseline?: string; report: string; allowDrift: boolean; json: boolean }
      ) => {
        try {
          const baselinePath = opts.baseline ?? defaultBaselinePath(skillPath);
          const baseline = readBaseline(baselinePath);
          const replay = replaySkill(skillPath, baseline);
          const report = diffAll(baseline, replay, { allowDrift: opts.allowDrift });
          writeReport(opts.report, report);

          if (opts.json) {
            process.stdout.write(JSON.stringify(report, null, 2) + '\n');
          } else {
            process.stdout.write(formatCheckResult(report, baseline.recordedAt) + '\n');
          }
          exitCode = report.exitCode;
        } catch (err) {
          exitCode = handleError(err);
        }
      }
    );

  program
    .command('report')
    .description('Print a previously generated evolveguard-report.json')
    .argument('[reportPath]', 'path to the report file', DEFAULT_REPORT_PATH)
    .option('--json', 'output structured JSON instead of human-readable text', false)
    .action((reportPath: string, opts: { json: boolean }) => {
      try {
        const report = readReport(reportPath);
        if (opts.json) {
          process.stdout.write(JSON.stringify(report, null, 2) + '\n');
        } else {
          process.stdout.write(formatReport(report) + '\n');
        }
        exitCode = report.exitCode;
      } catch (err) {
        exitCode = handleError(err);
      }
    });

  program
    .command('mcp')
    .description(
      '[coming soon] Expose record/check/report as MCP tools for a coding agent to call mid-session'
    )
    .action(() => {
      process.stdout.write(
        'evolveguard mcp is not implemented yet. Use `evolveguard record`/`check`/`report --json` directly from an agent for now.\n'
      );
      exitCode = 0;
    });

  function handleError(err: unknown): 1 | 2 {
    if (err instanceof EvolveGuardError) {
      process.stderr.write(err.message + '\n');
      return 2;
    }
    process.stderr.write(
      formatWhatWhyFix(
        'evolveguard crashed unexpectedly.',
        err instanceof Error ? err.message : String(err),
        'Please open an issue at https://github.com/RudrenduPaul/evolveguard/issues with the command you ran.'
      ) + '\n'
    );
    return 2;
  }

  try {
    await program.parseAsync(argv);
  } catch (err) {
    // exitOverride() makes commander throw a CommanderError instead of calling
    // process.exit() directly, so tests can assert on the return code. --help
    // and --version are commander.helpDisplayed / commander.version -> exit 0;
    // anything else (missing required option, unknown command, bad argument)
    // is a usage error -> exit 2, matching this CLI's documented exit-code contract.
    const code = (err as { code?: string; exitCode?: number }).code;
    if (code === 'commander.helpDisplayed' || code === 'commander.version') {
      return 0;
    }
    return 2;
  }
  return exitCode;
}

if (require.main === module) {
  runCli(process.argv).then(
    (code) => process.exit(code),
    (err) => {
      process.stderr.write(
        formatWhatWhyFix(
          'evolveguard crashed unexpectedly.',
          err instanceof Error ? err.message : String(err),
          'Please open an issue at https://github.com/RudrenduPaul/evolveguard/issues with the command you ran.'
        ) + '\n'
      );
      process.exit(2);
    }
  );
}
