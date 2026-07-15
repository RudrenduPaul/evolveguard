import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { parseSkillFile, deriveCapabilitySurface, inferHookEvidence } from './skillmd';

describe('parseSkillFile', () => {
  it('parses YAML frontmatter fields', () => {
    const content = `---
name: my-skill
description: does a thing
tools: [fs.read]
network: true
filesystem: read-write
scope: "./workspace/**"
hooks: ["hooks/pre.sh"]
---

Body text here.
`;
    const parsed = parseSkillFile(content, 'SKILL.md');
    expect(parsed.name).toBe('my-skill');
    expect(parsed.description).toBe('does a thing');
    expect(parsed.hasFrontmatter).toBe(true);
    expect(parsed.declaredScope).toEqual({
      tools: ['fs.read'],
      network: true,
      filesystem: 'read-write',
      scope: './workspace/**',
      hooks: ['hooks/pre.sh'],
    });
    expect(parsed.body.trim()).toBe('Body text here.');
  });

  it('falls back to defaults with no frontmatter (e.g. MEMORY.md)', () => {
    const content = 'Just prose, no frontmatter here.';
    const parsed = parseSkillFile(content, 'MEMORY.md');
    expect(parsed.name).toBe('MEMORY');
    expect(parsed.hasFrontmatter).toBe(false);
    expect(parsed.declaredScope).toEqual({
      tools: [],
      network: false,
      filesystem: 'none',
      scope: './**',
      hooks: [],
    });
    expect(parsed.body).toBe(content);
  });

  it('falls back to the file base name if frontmatter has no name field', () => {
    const content = '---\ndescription: no name here\n---\nbody';
    const parsed = parseSkillFile(content, '/a/b/my-file.md');
    expect(parsed.name).toBe('my-file');
  });

  it('tolerates malformed YAML frontmatter without throwing', () => {
    const content = '---\n: : not valid yaml : :\n---\nbody';
    const parsed = parseSkillFile(content, 'SKILL.md');
    expect(parsed.hasFrontmatter).toBe(true);
    expect(parsed.declaredScope.filesystem).toBe('none');
  });

  it('rejects an unknown filesystem value and defaults to none', () => {
    const content = '---\nfilesystem: delete-everything\n---\nbody';
    const parsed = parseSkillFile(content, 'SKILL.md');
    expect(parsed.declaredScope.filesystem).toBe('none');
  });
});

describe('deriveCapabilitySurface', () => {
  const tmpDir = path.join(os.tmpdir(), `evolveguard-test-${process.pid}-${Date.now()}`);

  beforeAll(() => {
    fs.mkdirSync(tmpDir, { recursive: true });
    fs.mkdirSync(path.join(tmpDir, 'hooks'), { recursive: true });
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('includes declared tools, network, and filesystem scope entries', () => {
    const parsed = parseSkillFile(
      '---\ntools: [custom.tool]\nnetwork: true\nfilesystem: read-write\nscope: "./workspace/**"\n---\nbody',
      'SKILL.md'
    );
    const surface = deriveCapabilitySurface(parsed, tmpDir);
    const tools = surface.map((e) => e.tool).sort();
    expect(tools).toEqual(['custom.tool', 'fs.read', 'fs.write', 'network.fetch']);
    const fsWrite = surface.find((e) => e.tool === 'fs.write');
    expect(fsWrite?.source).toBe('declared');
    expect(fsWrite?.scope).toBe('./workspace/**');
  });

  it('infers network/fs-write evidence from the skill body when no frontmatter is present', () => {
    const parsed = parseSkillFile(
      'This skill calls fetch("https://example.com") to sync state.',
      'MEMORY.md'
    );
    const surface = deriveCapabilitySurface(parsed, tmpDir);
    const networkEntry = surface.find((e) => e.tool === 'network.fetch');
    expect(networkEntry).toBeDefined();
    expect(networkEntry?.source).toBe('inferred');
    expect(networkEntry?.evidence?.[0]).toEqual({ file: '(body)', line: 1 });
  });

  it('infers evidence from a bundled hook script and stays within the skill directory', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'hooks', 'pre.sh'),
      '#!/bin/sh\ncurl https://example.com/upload\nrm -rf ./tmp\n'
    );
    const parsed = parseSkillFile('---\nhooks: ["hooks/pre.sh"]\n---\nbody', 'SKILL.md');
    const surface = deriveCapabilitySurface(parsed, tmpDir);
    const network = surface.find((e) => e.tool === 'network.fetch');
    const fsWrite = surface.find((e) => e.tool === 'fs.write');
    expect(network?.source).toBe('inferred');
    expect(fsWrite?.source).toBe('inferred');
    expect(network?.evidence?.[0].file).toBe('hooks/pre.sh');
  });

  it('does not duplicate a tool as inferred when it is already declared', () => {
    const parsed = parseSkillFile(
      '---\nfilesystem: read-write\nhooks: ["hooks/pre.sh"]\n---\nThis skill uses fs.writeFileSync internally.',
      'SKILL.md'
    );
    const surface = deriveCapabilitySurface(parsed, tmpDir);
    const fsWriteEntries = surface.filter((e) => e.tool === 'fs.write');
    expect(fsWriteEntries).toHaveLength(1);
    expect(fsWriteEntries[0].source).toBe('declared');
  });
});

describe('inferHookEvidence', () => {
  const tmpDir = path.join(
    os.tmpdir(),
    `evolveguard-hooks-test-${process.pid}-${Date.now()}`
  );

  beforeAll(() => {
    fs.mkdirSync(tmpDir, { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'ok.sh'), 'echo hello\n');
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('silently skips a hook path that escapes the skill directory', () => {
    const evidence = inferHookEvidence(tmpDir, ['../../etc/passwd']);
    expect(evidence.networkEvidence).toEqual([]);
    expect(evidence.fsWriteEvidence).toEqual([]);
  });

  it('silently skips a hook path that does not exist on disk', () => {
    const evidence = inferHookEvidence(tmpDir, ['does-not-exist.sh']);
    expect(evidence.networkEvidence).toEqual([]);
    expect(evidence.fsWriteEvidence).toEqual([]);
  });

  it('finds no evidence in a script with no network/fs-write calls', () => {
    const evidence = inferHookEvidence(tmpDir, ['ok.sh']);
    expect(evidence.networkEvidence).toEqual([]);
    expect(evidence.fsWriteEvidence).toEqual([]);
  });
});
