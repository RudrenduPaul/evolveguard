import * as fs from 'node:fs';
import * as path from 'node:path';
import { parse as parseYaml } from 'yaml';
import type {
  CapabilityEntry,
  CapabilitySurface,
  DeclaredScope,
  ParsedSkillFile,
} from '../types';
import { resolveWithinBase } from '../paths';

/**
 * Parses a Claude Agent Skill file (SKILL.md) or an auto-memory file
 * (MEMORY.md). SKILL.md files carry YAML frontmatter declaring the skill's
 * name and scope; MEMORY.md files typically do not, so a file with no
 * frontmatter is treated as declaring an empty scope, and its capability
 * surface is derived entirely from static evidence found in its own body
 * text (see deriveCapabilitySurface below).
 *
 * Frontmatter schema this parser understands:
 *   ---
 *   name: my-skill
 *   description: ...
 *   tools: [fs.read, fs.write]     # declared tool names, optional
 *   network: false                  # boolean, optional (default false)
 *   filesystem: read-only           # "none" | "read-only" | "read-write", optional (default none)
 *   scope: "./workspace/**"         # glob the filesystem tools are scoped to, optional (default "./**")
 *   hooks: ["scripts/pre-run.sh"]   # bundled hook scripts, paths relative to the skill file, optional
 *   ---
 *
 * This schema is a superset compatible with SkillGuard's own
 * `DeclaredScope` (network: boolean, filesystem: none|read-only|read-write)
 * -- EvolveGuard reuses the same field names and parsing pattern
 * deliberately so a skill author only has to think about one frontmatter
 * shape across both tools.
 */

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---/;

const KNOWN_FILESYSTEM_VALUES = new Set(['none', 'read-only', 'read-write']);

export function parseSkillFile(content: string, fileBaseName: string): ParsedSkillFile {
  const match = FRONTMATTER_RE.exec(content);

  if (!match) {
    return {
      name: path.basename(fileBaseName, path.extname(fileBaseName)),
      hasFrontmatter: false,
      declaredScope: {
        tools: [],
        network: false,
        filesystem: 'none',
        scope: './**',
        hooks: [],
      },
      body: content,
    };
  }

  let data: unknown;
  try {
    data = parseYaml(match[1]);
  } catch {
    data = null;
  }

  const record =
    typeof data === 'object' && data !== null ? (data as Record<string, unknown>) : {};

  const name =
    typeof record.name === 'string' && record.name.trim().length > 0
      ? record.name.trim()
      : path.basename(fileBaseName, path.extname(fileBaseName));

  const description =
    typeof record.description === 'string' ? record.description : undefined;

  const tools = Array.isArray(record.tools)
    ? record.tools.filter((t): t is string => typeof t === 'string')
    : [];

  const network = record.network === true;

  const filesystemRaw =
    typeof record.filesystem === 'string' ? record.filesystem : 'none';
  const filesystem: DeclaredScope['filesystem'] = KNOWN_FILESYSTEM_VALUES.has(
    filesystemRaw
  )
    ? (filesystemRaw as DeclaredScope['filesystem'])
    : 'none';

  const scope =
    typeof record.scope === 'string' && record.scope.trim().length > 0
      ? record.scope
      : './**';

  const hooks = Array.isArray(record.hooks)
    ? record.hooks.filter((h): h is string => typeof h === 'string')
    : [];

  const body = content.slice(match[0].length);

  return {
    name,
    description,
    hasFrontmatter: true,
    declaredScope: { tools, network, filesystem, scope, hooks },
    body,
  };
}

// Note: `curl`/`wget` deliberately have no trailing `\s` baked into the
// alternation -- `\b` after "curl" already requires a non-word character to
// follow (a space, a flag like "-X", end of string, all count), so
// consuming the whitespace into the match would break that boundary check
// whenever the very next character after the space is itself non-word (e.g.
// "curl -X ..."), silently missing real command lines.
const NETWORK_EVIDENCE_RE =
  /\b(fetch|axios|http\.request|https\.request|requests\.(get|post|put|delete)|urllib\.request|urlopen|socket\.socket|curl|wget)\b/i;

const FS_WRITE_EVIDENCE_RE =
  /\b(fs\.writeFile|fs\.writeFileSync|fs\.appendFile|fs\.unlink|open\([^)]*['"]w|os\.remove|os\.rmdir|shutil\.rmtree)\b|>\s*\/|rm\s+-rf/i;

function firstMatchLine(content: string, re: RegExp): number | null {
  const m = re.exec(content);
  if (!m) return null;
  let line = 1;
  for (let i = 0; i < m.index; i++) {
    if (content.charCodeAt(i) === 10) line++;
  }
  return line;
}

/**
 * Reads a skill's declared hook scripts (paths validated against the
 * skill's own directory -- see paths.ts) and scans each for static evidence
 * of network or filesystem-write behavior. This is the same read-only,
 * regex-based evidence model SkillGuard uses; EvolveGuard never executes
 * anything from the skill or its hooks.
 */
export function inferHookEvidence(
  skillDir: string,
  hooks: string[]
): {
  networkEvidence: { file: string; line: number }[];
  fsWriteEvidence: { file: string; line: number }[];
} {
  const networkEvidence: { file: string; line: number }[] = [];
  const fsWriteEvidence: { file: string; line: number }[] = [];

  for (const hookPath of hooks) {
    let absPath: string;
    try {
      absPath = resolveWithinBase(skillDir, hookPath);
    } catch {
      continue;
    }

    let content: string;
    try {
      content = fs.readFileSync(absPath, 'utf8');
    } catch {
      continue;
    }

    const netLine = firstMatchLine(content, NETWORK_EVIDENCE_RE);
    if (netLine !== null) {
      networkEvidence.push({ file: hookPath, line: netLine });
    }

    const fsLine = firstMatchLine(content, FS_WRITE_EVIDENCE_RE);
    if (fsLine !== null) {
      fsWriteEvidence.push({ file: hookPath, line: fsLine });
    }
  }

  return { networkEvidence, fsWriteEvidence };
}

/**
 * Derives the full capability surface for a parsed skill: declared entries
 * from frontmatter, plus inferred entries from static evidence in the
 * skill's own body text and any bundled hook scripts. This is the
 * deterministic "transcript baseline" EvolveGuard records and later
 * re-derives on replay -- see README "How it works" for why this is not a
 * live LLM run.
 */
export function deriveCapabilitySurface(
  parsed: ParsedSkillFile,
  skillDir: string
): CapabilitySurface {
  const entries: CapabilityEntry[] = [];
  const seen = new Set<string>();

  const addDeclared = (tool: string, scope?: string) => {
    const key = `declared:${tool}`;
    if (seen.has(key)) return;
    seen.add(key);
    entries.push({ tool, source: 'declared', scope });
  };

  for (const tool of parsed.declaredScope.tools) {
    addDeclared(tool);
  }

  if (parsed.declaredScope.network) {
    addDeclared('network.fetch');
  }

  if (
    parsed.declaredScope.filesystem === 'read-only' ||
    parsed.declaredScope.filesystem === 'read-write'
  ) {
    addDeclared('fs.read', parsed.declaredScope.scope);
  }
  if (parsed.declaredScope.filesystem === 'read-write') {
    addDeclared('fs.write', parsed.declaredScope.scope);
  }

  // Inferred evidence from the skill body itself (covers MEMORY.md, which has no frontmatter).
  const bodyNetLine = firstMatchLine(parsed.body, NETWORK_EVIDENCE_RE);
  const bodyFsLine = firstMatchLine(parsed.body, FS_WRITE_EVIDENCE_RE);

  const inferredNetworkEvidence =
    bodyNetLine !== null ? [{ file: '(body)', line: bodyNetLine }] : [];
  const inferredFsEvidence =
    bodyFsLine !== null ? [{ file: '(body)', line: bodyFsLine }] : [];

  // Inferred evidence from bundled hook scripts declared in frontmatter.
  const hookEvidence = inferHookEvidence(skillDir, parsed.declaredScope.hooks);
  inferredNetworkEvidence.push(...hookEvidence.networkEvidence);
  inferredFsEvidence.push(...hookEvidence.fsWriteEvidence);

  const addInferred = (tool: string, evidence: { file: string; line: number }[]) => {
    if (evidence.length === 0) return;
    const key = `inferred:${tool}`;
    if (seen.has(key)) {
      // Merge evidence into the existing entry if one was already pushed (shouldn't happen given the keying above, kept for safety).
      const existing = entries.find((e) => e.source === 'inferred' && e.tool === tool);
      if (existing) existing.evidence = [...(existing.evidence ?? []), ...evidence];
      return;
    }
    // If this tool is already declared, do not duplicate it as a separate inferred entry --
    // declared coverage takes precedence and the inferred evidence is redundant confirmation.
    if (seen.has(`declared:${tool}`)) return;
    seen.add(key);
    entries.push({ tool, source: 'inferred', evidence });
  };

  addInferred('network.fetch', inferredNetworkEvidence);
  addInferred('fs.write', inferredFsEvidence);

  return entries;
}
