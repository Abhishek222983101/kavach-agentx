#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();

let raw = '';
process.stdin.setEncoding('utf8');
for await (const chunk of process.stdin) raw += chunk;

let input = {};
try {
  input = JSON.parse(raw);
} catch {
  process.exit(0);
}

if (input.stop_hook_active) process.exit(0);

const stateDir = path.join(root, '.claude', 'state');
fs.mkdirSync(stateDir, { recursive: true });
const nudgePath = path.join(stateDir, 'last-stop-nudge');
const now = Date.now();

try {
  const last = Number(fs.readFileSync(nudgePath, 'utf8'));
  if (Number.isFinite(last) && now - last < 10 * 60 * 1000) process.exit(0);
} catch {
  // first run
}

function git(args) {
  try {
    return execFileSync('git', args, {
      cwd: root,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    });
  } catch {
    return '';
  }
}

const status = git(['status', '--porcelain']);
if (!status.trim()) process.exit(0);

const changed = status
  .split('\n')
  .map((line) => line.slice(3).trim())
  .filter(Boolean)
  .flatMap((file) => (file.includes(' -> ') ? file.split(' -> ') : [file]));

const codeExt = /\.(ts|tsx|js|jsx|mjs|cjs|py|rb|go|rs|java|kt|php|cs|swift|vue|svelte|astro|sql|prisma|html|css|scss|sh|yml|yaml|json|toml)$/i;

const isMachineLog = (file) =>
  file === 'docs/05-SESSIONS/PROMPT-LOG.md' ||
  file.startsWith('docs/05-SESSIONS/raw/') ||
  file === 'docs/state.json';

const isNotebook = (file) =>
  !isMachineLog(file) &&
  (file.startsWith('docs/') || file === 'AGENTS.md' || file === 'CLAUDE.md');

const codeChanged = changed.some((file) => codeExt.test(file) && !file.startsWith('docs/') && !isMachineLog(file));
const notebookChanged = changed.some(isNotebook);

if (!codeChanged || notebookChanged) process.exit(0);

fs.writeFileSync(nudgePath, String(now));

console.log(
  JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'Stop',
      additionalContext:
        'Doc sync check: code changed but no notebook file changed in this working tree. Before ending, run the doc-sync skill. Update the documents affected by this change, then write the SESSION-LOG entry and update docs/state.json. If the change really was trivial, record that in SESSION-LOG.md and update state.json anyway.',
    },
  })
);
