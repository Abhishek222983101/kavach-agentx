#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const now = new Date();
const stamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

const state = readJson(path.join(root, 'docs', 'state.json'), {});
const rawName = state.project_name || path.basename(root) || 'project';
const slug =
  rawName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60) || 'project';

const handoffRoot = path.join(root, 'handoff');
const finalDir = path.join(handoffRoot, `${slug}-${stamp}`);
const packageDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pck-handoff-'));
fs.mkdirSync(handoffRoot, { recursive: true });

const skipNames = new Set([
  'node_modules',
  '.git',
  'handoff',
  '.next',
  'dist',
  'build',
  'out',
  'coverage',
  '.turbo',
  '.cache',
  '.venv',
  'venv',
  '__pycache__',
  '.pytest_cache',
  '.mypy_cache',
  '.idea',
  '.vscode',
  '.DS_Store',
]);

function isEnvFile(name) {
  if (!/^\.env($|\.)/.test(name)) return false;
  return !/\.(example|sample|template)$/i.test(name);
}

function shouldSkip(src) {
  const name = path.basename(src);
  const normalized = src.split(path.sep).join('/');
  if (skipNames.has(name)) return true;
  if (normalized.includes('/.claude/state')) return true;
  if (isEnvFile(name)) return true;
  if (/\.(pem|key|p12|pfx)$/i.test(name)) return true;
  if (/\.log$/i.test(name)) return true;
  return false;
}

function copy(src, dest) {
  if (!fs.existsSync(src)) return;
  fs.cpSync(src, dest, { recursive: true, filter: (s) => !shouldSkip(s) });
}

// 1. Notebook and kit
copy(path.join(root, 'docs'), path.join(packageDir, 'docs'));
for (const file of ['AGENTS.md', 'CLAUDE.md']) {
  copy(path.join(root, file), path.join(packageDir, file));
}
copy(path.join(root, 'README.md'), path.join(packageDir, 'kit', 'README.md'));
copy(path.join(root, '.claude', 'skills'), path.join(packageDir, 'kit', '.claude', 'skills'));
copy(path.join(root, '.claude', 'hooks'), path.join(packageDir, 'kit', '.claude', 'hooks'));
copy(path.join(root, '.claude', 'settings.json'), path.join(packageDir, 'kit', '.claude', 'settings.json'));
copy(path.join(root, 'tools'), path.join(packageDir, 'kit', 'tools'));

// 2. Full code snapshot (no secrets, deps, or VCS internals)
const codeDir = path.join(packageDir, 'code');
copy(root, codeDir);

// 3. Manifests
const manifestDir = path.join(packageDir, 'meta');
fs.mkdirSync(manifestDir, { recursive: true });
const manifestFiles = [
  'package.json',
  'package-lock.json',
  'pnpm-lock.yaml',
  'pnpm-workspace.yaml',
  'yarn.lock',
  'bun.lockb',
  'requirements.txt',
  'pyproject.toml',
  'Pipfile',
  'poetry.lock',
  'Cargo.toml',
  'Cargo.lock',
  'go.mod',
  'go.sum',
  'composer.json',
  'composer.lock',
  'Gemfile',
  'Gemfile.lock',
  'deno.json',
  'bunfig.toml',
];

for (const file of manifestFiles) {
  const src = path.join(root, file);
  if (fs.existsSync(src)) {
    fs.mkdirSync(path.join(manifestDir, 'manifests'), { recursive: true });
    fs.copyFileSync(src, path.join(manifestDir, 'manifests', file));
  }
}

// 4. Env var names only (never values)
const envNames = new Set();
const envExampleFiles = [];
function collectEnvFiles(dir, depth) {
  if (depth > 3) return;
  let entries = [];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    if (entry.name === 'node_modules' || entry.name === '.git' || entry.name === 'handoff') continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      collectEnvFiles(full, depth + 1);
    } else if (/^\.env($|\.)/.test(entry.name) && /\.(example|sample|template)$/i.test(entry.name)) {
      envExampleFiles.push(full);
      try {
        const text = fs.readFileSync(full, 'utf8');
        for (const line of text.split('\n')) {
          const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=/);
          if (match) envNames.add(match[1]);
        }
      } catch {
        // ignore
      }
    }
  }
}
collectEnvFiles(root, 0);

fs.writeFileSync(
  path.join(manifestDir, 'env-vars.txt'),
  [
    'Environment variable names found in example files.',
    'Values are intentionally omitted.',
    '',
    ...[...envNames].sort(),
    '',
    `Source files: ${envExampleFiles.map((f) => path.relative(root, f)).join(', ') || 'none found'}`,
    '',
  ].join('\n')
);

// 5. Git history, status, diff
function git(args) {
  try {
    return execFileSync('git', args, {
      cwd: root,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      maxBuffer: 20 * 1024 * 1024,
    });
  } catch {
    return '';
  }
}

const isGit = fs.existsSync(path.join(root, '.git'));
let gitSummary = {};
if (isGit) {
  const info = [
    '# Git information',
    '',
    'Remote:',
    git(['remote', '-v']) || '(none)',
    '',
    'Branch:',
    git(['branch', '--show-current']) || '(unknown)',
    '',
    'HEAD:',
    git(['rev-parse', 'HEAD']) || '(no commits)',
    '',
    'Recent commits:',
    git(['log', '--oneline', '-30']) || '(no commits)',
    '',
    'Working tree status:',
    git(['status', '--porcelain']) || '(clean)',
    '',
    'Diff stat:',
    git(['diff', '--stat']) || '(no unstaged changes)',
    '',
  ].join('\n');
  fs.writeFileSync(path.join(manifestDir, 'git-info.txt'), info);

  const diff = git(['diff']);
  const cappedDiff =
    diff.length > 2 * 1024 * 1024 ? diff.slice(0, 2 * 1024 * 1024) + '\n\n[DIFF TRUNCATED AT 2 MB]' : diff;
  fs.writeFileSync(path.join(manifestDir, 'changes.patch'), cappedDiff || '(no unstaged diff)');

  try {
    execFileSync('git', ['bundle', 'create', path.join(manifestDir, 'git-history.bundle'), '--all'], {
      cwd: root,
      stdio: 'ignore',
    });
  } catch {
    // no commits or bundle failed; git-info still records the state
  }

  gitSummary = {
    remote: git(['remote', '-v']).trim(),
    branch: git(['branch', '--show-current']).trim(),
    head: git(['rev-parse', 'HEAD']).trim(),
    dirty: Boolean(git(['status', '--porcelain']).trim()),
  };
}

// 6. File tree
const treeLines = [];
function walk(dir, prefix) {
  if (treeLines.length > 5000) return;
  let entries = [];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    return;
  }
  for (const entry of entries) {
    if (skipNames.has(entry.name) || entry.name === '.DS_Store') continue;
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    treeLines.push((entry.isDirectory() ? `${rel}/` : rel));
    if (entry.isDirectory()) walk(path.join(dir, entry.name), rel);
  }
}
walk(codeDir, '');
fs.writeFileSync(path.join(manifestDir, 'file-tree.txt'), treeLines.join('\n') + '\n');

// 7. Secret scan (report locations, never values)
const secretPatterns = [
  { name: 'OpenAI/Anthropic-style key', re: /\bsk-[A-Za-z0-9_-]{20,}/ },
  { name: 'GitHub token', re: /\b(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})/ },
  { name: 'Google API key', re: /\bAIza[0-9A-Za-z_-]{20,}/ },
  { name: 'Slack token', re: /\bxox[baprs]-[A-Za-z0-9-]{10,}/ },
  { name: 'AWS access key', re: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: 'Private key block', re: /-----BEGIN [A-Z ]*PRIVATE KEY-----/ },
  { name: 'Database URL', re: /\b(mongodb(\+srv)?|postgres(ql)?|mysql|redis):\/\/[^\s'"]+/i },
  { name: 'Stripe secret', re: /\bSTRIPE_[A-Z_]*SECRET[A-Z_]*\s*=\s*\S+/i },
  { name: 'Supabase service role', re: /\bSUPABASE_SERVICE_ROLE_KEY\s*=\s*\S+/i },
];

const textExt = /\.(js|mjs|cjs|ts|tsx|jsx|json|md|txt|ya?ml|env|example|py|rb|go|rs|php|java|kt|swift|sh|sql|prisma|html|css|scss|vue|svelte|astro|toml)$/i;
const secretWarnings = [];
function scan(dir) {
  let entries = [];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    if (entry.name === 'node_modules' || entry.name === '.git') continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      scan(full);
      continue;
    }
    if (!textExt.test(entry.name)) continue;
    let text = '';
    try {
      const stat = fs.statSync(full);
      if (stat.size > 1024 * 1024) continue;
      text = fs.readFileSync(full, 'utf8');
    } catch {
      continue;
    }
    const lines = text.split('\n');
    for (let i = 0; i < lines.length; i += 1) {
      for (const pattern of secretPatterns) {
        if (pattern.re.test(lines[i])) {
          secretWarnings.push({
            file: path.relative(packageDir, full),
            line: i + 1,
            type: pattern.name,
          });
        }
      }
      if (secretWarnings.length >= 50) return;
    }
  }
}
scan(codeDir);
fs.writeFileSync(
  path.join(manifestDir, 'secret-scan.txt'),
  secretWarnings.length
    ? [
        'Possible secrets found. Values are not shown.',
        'Rotate anything real before sharing this package.',
        '',
        ...secretWarnings.map((w) => `${w.file}:${w.line} — ${w.type}`),
        '',
      ].join('\n')
    : 'No obvious secret patterns found in the snapshot.\n'
);

// 8. Manifest
const docStatus = {};
for (const file of [
  '00-START-HERE.md',
  '01-BUSINESS/BUSINESS-CONTEXT.md',
  '01-BUSINESS/DEEP-CONTEXT.md',
  '01-BUSINESS/DOMAIN-CHECKLIST.md',
  '02-PRODUCT/PRD.md',
  '02-PRODUCT/WORKFLOWS.md',
  '03-SYSTEM/SYSTEM-ARCHITECTURE.md',
  '03-SYSTEM/DATA-MODEL.md',
  '03-SYSTEM/INTEGRATIONS.md',
  '04-DELIVERY/BUILD-PLAN.md',
  '04-DELIVERY/CURRENT-STATE.md',
  '04-DELIVERY/SCENARIOS.md',
  '04-DELIVERY/DECISIONS.md',
  '04-DELIVERY/OPEN-QUESTIONS.md',
  '05-SESSIONS/SESSION-LOG.md',
  '05-SESSIONS/PROMPTING-PATTERNS.md',
  '06-HANDOFF/HANDOFF.md',
  '06-HANDOFF/CHANGELOG.md',
]) {
  const text = fs.existsSync(path.join(packageDir, 'docs', file))
    ? fs.readFileSync(path.join(packageDir, 'docs', file), 'utf8')
    : '';
  const match = text.match(/^---[\s\S]*?\bstatus:\s*([a-zA-Z-]+)[\s\S]*?---/m);
  docStatus[file] = match ? match[1] : fs.existsSync(path.join(packageDir, 'docs', file)) ? 'unknown' : 'missing';
}

const manifest = {
  generator: 'Project Context Kit',
  generated_at: now.toISOString(),
  project: rawName,
  project_state: state,
  git: gitSummary,
  environment: {
    platform: process.platform,
    node: process.version,
    hostname: (await import('node:os')).hostname(),
  },
  docs: docStatus,
  env_var_names: [...envNames].sort(),
  env_example_files: envExampleFiles.map((f) => path.relative(root, f)),
  secret_warnings: secretWarnings,
  package: {
    directory: path.basename(finalDir),
    code_snapshot: 'code/',
    notebook: 'docs/',
    kit: 'kit/',
    meta: 'meta/',
  },
};
fs.writeFileSync(path.join(packageDir, 'manifest.json'), JSON.stringify(manifest, null, 2));

// 9. Read-me for the recipient
fs.writeFileSync(
  path.join(packageDir, 'README-FIRST.txt'),
  [
    'PROJECT CONTEXT KIT — HANDOFF PACKAGE',
    '',
    'Start with: docs/06-HANDOFF/HANDOFF.md',
    '',
    'What is inside:',
    '  docs/                    the project notebook (business, product, workflows, architecture, delivery, sessions)',
    '  code/                    a snapshot of the project, excluding node_modules, .git, .env and build output',
    '  kit/                     the skills, hooks and tools that kept the notebook current',
    '  meta/git-info.txt        remote, branch, HEAD, recent commits, working tree status',
    '  meta/git-history.bundle  full git history (clone it with: git clone meta/git-history.bundle repo)',
    '  meta/changes.patch       uncommitted diff at handoff time',
    '  meta/env-vars.txt        required environment variable names only; no values',
    '  meta/file-tree.txt       snapshot file tree',
    '  meta/secret-scan.txt     possible secret locations; values are not shown',
    '  manifest.json            machine-readable package index',
    '',
    'Read order for the receiving team:',
    '  1. docs/06-HANDOFF/HANDOFF.md',
    '  2. docs/04-DELIVERY/CURRENT-STATE.md',
    '  3. docs/03-SYSTEM/SYSTEM-ARCHITECTURE.md',
    '  4. docs/02-PRODUCT/PRD.md and docs/02-PRODUCT/WORKFLOWS.md',
    '  5. docs/01-BUSINESS/DEEP-CONTEXT.md',
    '  6. docs/05-SESSIONS/SESSION-LOG.md and docs/05-SESSIONS/PROMPTING-PATTERNS.md',
    '',
    'Security: .env files are excluded. If meta/secret-scan.txt reports a real secret, rotate it before sharing.',
    '',
  ].join('\n')
);

// 10. Zip (or tar.gz fallback)
let archive = '';
try {
  const zipPath = path.join(handoffRoot, `${slug}-${stamp}.zip`);
  execFileSync('zip', ['-rq', zipPath, '.'], { cwd: packageDir, stdio: 'ignore' });
  archive = zipPath;
} catch {
  try {
    const tarPath = path.join(handoffRoot, `${slug}-${stamp}.tar.gz`);
    execFileSync('tar', ['-czf', tarPath, '-C', packageDir, '.'], { stdio: 'ignore' });
    archive = tarPath;
  } catch {
    archive = '';
  }
}

fs.cpSync(packageDir, finalDir, { recursive: true });
fs.rmSync(packageDir, { recursive: true, force: true });

console.log('Handoff package built.');
console.log(`Folder: ${path.relative(root, finalDir)}`);
if (archive) console.log(`Archive: ${path.relative(root, archive)}`);
console.log('');
console.log(`Docs: ${Object.values(docStatus).filter((s) => s === 'filled').length} filled, ${Object.values(docStatus).filter((s) => s === 'partial').length} partial, ${Object.values(docStatus).filter((s) => s === 'empty').length} empty`);
console.log(`Env var names: ${envNames.size}`);
console.log(`Secret warnings: ${secretWarnings.length}`);
if (secretWarnings.length) console.log('See meta/secret-scan.txt. Rotate anything real before sharing.');
console.log('');
console.log('Next: fill docs/06-HANDOFF/HANDOFF.md, then run node tools/check-docs.mjs.');
