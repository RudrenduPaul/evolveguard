import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { runCli } from './cli';

describe('evolveguard CLI', () => {
  let tmpDir: string;
  let stdout: string[];
  let stderr: string[];
  let stdoutSpy: ReturnType<typeof vi.spyOn>;
  let stderrSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'evolveguard-cli-test-'));
    stdout = [];
    stderr = [];
    stdoutSpy = vi.spyOn(process.stdout, 'write').mockImplementation((chunk: unknown) => {
      stdout.push(String(chunk));
      return true;
    });
    stderrSpy = vi.spyOn(process.stderr, 'write').mockImplementation((chunk: unknown) => {
      stderr.push(String(chunk));
      return true;
    });
  });

  afterEach(() => {
    stdoutSpy.mockRestore();
    stderrSpy.mockRestore();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  function writeSkill(content: string): string {
    const p = path.join(tmpDir, 'SKILL.md');
    fs.writeFileSync(p, content);
    return p;
  }

  function writeFixtures(fixtures: unknown): string {
    const p = path.join(tmpDir, 'fixtures.json');
    fs.writeFileSync(p, JSON.stringify(fixtures));
    return p;
  }

  it('record writes a baseline file and exits 0', async () => {
    const skillPath = writeSkill('---\nname: demo\nfilesystem: read-only\n---\nbody');
    const fixturesPath = writeFixtures([
      { id: 'f1', prompt: 'read a file', expectedToolCalls: [{ tool: 'fs.read' }] },
    ]);

    const code = await runCli([
      'node',
      'evolveguard',
      'record',
      skillPath,
      '--fixtures',
      fixturesPath,
    ]);

    expect(code).toBe(0);
    const baselinePath = path.join(tmpDir, '.evolveguard-baseline.json');
    expect(fs.existsSync(baselinePath)).toBe(true);
    expect(stdout.join('')).toContain('Baseline Recorded');
  });

  it('check exits 0 with PASS when nothing changed', async () => {
    const skillPath = writeSkill('---\nname: demo\nfilesystem: read-only\n---\nbody');
    const fixturesPath = writeFixtures([
      { id: 'f1', prompt: 'read a file', expectedToolCalls: [{ tool: 'fs.read' }] },
    ]);
    await runCli([
      'node',
      'evolveguard',
      'record',
      skillPath,
      '--fixtures',
      fixturesPath,
    ]);

    const reportPath = path.join(tmpDir, 'evolveguard-report.json');
    const code = await runCli([
      'node',
      'evolveguard',
      'check',
      skillPath,
      '--report',
      reportPath,
    ]);

    expect(code).toBe(0);
    expect(stdout.join('')).toContain('[PASS]');
    expect(fs.existsSync(reportPath)).toBe(true);
  });

  it('check exits 1 with DRIFT when the skill gains a new declared capability', async () => {
    const skillPath = writeSkill('---\nname: demo\nfilesystem: read-only\n---\nbody');
    const fixturesPath = writeFixtures([
      {
        id: 'f1',
        prompt: 'scan a monorepo',
        expectedToolCalls: [{ tool: 'fs.read' }, { tool: 'fs.write' }],
      },
    ]);
    await runCli([
      'node',
      'evolveguard',
      'record',
      skillPath,
      '--fixtures',
      fixturesPath,
    ]);

    fs.writeFileSync(skillPath, '---\nname: demo\nfilesystem: read-write\n---\nbody');
    const reportPath = path.join(tmpDir, 'evolveguard-report.json');
    const code = await runCli([
      'node',
      'evolveguard',
      'check',
      skillPath,
      '--report',
      reportPath,
    ]);

    expect(code).toBe(1);
    expect(stdout.join('')).toContain('[DRIFT]');
    expect(stdout.join('')).toContain('new tool call: fs.write');
  });

  it('check --allow-drift exits 0 even with drift detected', async () => {
    const skillPath = writeSkill('---\nname: demo\nfilesystem: read-only\n---\nbody');
    const fixturesPath = writeFixtures([
      {
        id: 'f1',
        prompt: 'scan a monorepo',
        expectedToolCalls: [{ tool: 'fs.read' }, { tool: 'fs.write' }],
      },
    ]);
    await runCli([
      'node',
      'evolveguard',
      'record',
      skillPath,
      '--fixtures',
      fixturesPath,
    ]);
    fs.writeFileSync(skillPath, '---\nname: demo\nfilesystem: read-write\n---\nbody');
    const reportPath = path.join(tmpDir, 'evolveguard-report.json');

    const code = await runCli([
      'node',
      'evolveguard',
      'check',
      skillPath,
      '--allow-drift',
      '--report',
      reportPath,
    ]);

    expect(code).toBe(0);
    expect(stdout.join('')).toContain('[DRIFT]');
  });

  it('check --json outputs structured JSON matching the report schema', async () => {
    const skillPath = writeSkill('---\nname: demo\nfilesystem: read-only\n---\nbody');
    const fixturesPath = writeFixtures([
      { id: 'f1', prompt: 'read a file', expectedToolCalls: [{ tool: 'fs.read' }] },
    ]);
    await runCli([
      'node',
      'evolveguard',
      'record',
      skillPath,
      '--fixtures',
      fixturesPath,
    ]);

    stdout.length = 0;
    const reportPath = path.join(tmpDir, 'evolveguard-report.json');
    const code = await runCli([
      'node',
      'evolveguard',
      'check',
      skillPath,
      '--json',
      '--report',
      reportPath,
    ]);

    expect(code).toBe(0);
    const parsed = JSON.parse(stdout.join(''));
    expect(parsed.summary).toEqual({ pass: 1, drift: 0, total: 1 });
    expect(parsed.exitCode).toBe(0);
  });

  it('report prints a previously written report file', async () => {
    const skillPath = writeSkill('---\nname: demo\nfilesystem: read-only\n---\nbody');
    const fixturesPath = writeFixtures([
      { id: 'f1', prompt: 'read a file', expectedToolCalls: [{ tool: 'fs.read' }] },
    ]);
    await runCli([
      'node',
      'evolveguard',
      'record',
      skillPath,
      '--fixtures',
      fixturesPath,
    ]);
    const reportPath = path.join(tmpDir, 'evolveguard-report.json');
    await runCli(['node', 'evolveguard', 'check', skillPath, '--report', reportPath]);
    stdout.length = 0;

    const code = await runCli(['node', 'evolveguard', 'report', reportPath]);

    expect(code).toBe(0);
    expect(stdout.join('')).toContain('EvolveGuard');
  });

  it('check exits 2 with a WHAT/WHY/FIX error when no baseline exists', async () => {
    const skillPath = writeSkill('---\nname: demo\n---\nbody');
    const code = await runCli(['node', 'evolveguard', 'check', skillPath]);
    expect(code).toBe(2);
    expect(stderr.join('')).toContain('WHAT:');
    expect(stderr.join('')).toContain('WHY:');
    expect(stderr.join('')).toContain('FIX:');
  });

  it('record exits 2 when the fixtures file is malformed', async () => {
    const skillPath = writeSkill('---\nname: demo\n---\nbody');
    const badFixtures = path.join(tmpDir, 'bad.json');
    fs.writeFileSync(badFixtures, '{not json');

    const code = await runCli([
      'node',
      'evolveguard',
      'record',
      skillPath,
      '--fixtures',
      badFixtures,
    ]);

    expect(code).toBe(2);
    expect(stderr.join('')).toContain('WHAT:');
  });

  it('mcp prints a coming-soon message and exits 0', async () => {
    const code = await runCli(['node', 'evolveguard', 'mcp']);
    expect(code).toBe(0);
    expect(stdout.join('')).toContain('not implemented yet');
  });

  it('exits 0 and prints help text for --help', async () => {
    const code = await runCli(['node', 'evolveguard', '--help']);
    expect(code).toBe(0);
  });

  it('exits 2 for an unknown subcommand', async () => {
    const code = await runCli(['node', 'evolveguard', 'not-a-real-command']);
    expect(code).toBe(2);
  });

  it('exits 2 when --fixtures is omitted from record', async () => {
    const skillPath = writeSkill('---\nname: demo\n---\nbody');
    const code = await runCli(['node', 'evolveguard', 'record', skillPath]);
    expect(code).toBe(2);
  });
});
