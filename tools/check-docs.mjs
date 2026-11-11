#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();

const required = [
  'docs/00-START-HERE.md',
  'docs/01-BUSINESS/BUSINESS-CONTEXT.md',
  'docs/01-BUSINESS/DEEP-CONTEXT.md',
  'docs/01-BUSINESS/DOMAIN-CHECKLIST.md',
  'docs/02-PRODUCT/PRD.md',
  'docs/02-PRODUCT/WORKFLOWS.md',
  'docs/03-SYSTEM/SYSTEM-ARCHITECTURE.md',
  'docs/03-SYSTEM/DATA-MODEL.md',
  'docs/03-SYSTEM/INTEGRATIONS.md',
  'docs/04-DELIVERY/BUILD-PLAN.md',
  'docs/04-DELIVERY/CURRENT-STATE.md',
  'docs/04-DELIVERY/SCENARIOS.md',
  'docs/04-DELIVERY/DECISIONS.md',
  'docs/04-DELIVERY/OPEN-QUESTIONS.md',
  'docs/05-SESSIONS/SESSION-LOG.md',
  'docs/05-SESSIONS/PROMPTING-PATTERNS.md',
  'docs/06-HANDOFF/HANDOFF.md',
  'docs/06-HANDOFF/CHANGELOG.md',
];

const critical = new Set([
  'docs/02-PRODUCT/PRD.md',
  'docs/02-PRODUCT/WORKFLOWS.md',
  'docs/03-SYSTEM/SYSTEM-ARCHITECTURE.md',
  'docs/04-DELIVERY/CURRENT-STATE.md',
  'docs/06-HANDOFF/HANDOFF.md',
]);

function read(file) {
  try {
    return fs.readFileSync(path.join(root, file), 'utf8');
  } catch {
    return null;
  }
}

function statusOf(text) {
  if (!text) return 'missing';
  const match = text.match(/^---[\s\S]*?\bstatus:\s*([a-zA-Z-]+)[\s\S]*?---/m);
  if (match) return match[1].toLowerCase();
  if (/status:\s*empty/i.test(text)) return 'empty';
  if (/status:\s*partial/i.test(text)) return 'partial';
  if (/status:\s*filled/i.test(text)) return 'filled';
  return 'unknown';
}

function count(text, needle) {
  if (!text) return 0;
  const body = text
    .split('\n')
    .filter((line) => !line.includes('Truth labels:'))
    .join('\n');
  return (body.match(new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
}

const rows = [];
let score = 0;
let present = 0;
let totalUnknown = 0;
let totalAssumed = 0;
let totalConfirmed = 0;
let totalObserved = 0;

for (const file of required) {
  const text = read(file);
  const status = statusOf(text);
  if (text) present += 1;
  if (status === 'filled') score += 1;
  else if (status === 'partial') score += 0.5;

  totalUnknown += count(text, '[UNKNOWN]');
  totalAssumed += count(text, '[ASSUMED]');
  totalConfirmed += count(text, '[CONFIRMED]');
  totalObserved += count(text, '[OBSERVED]');

  rows.push({ file, status, unknown: count(text, '[UNKNOWN]'), critical: critical.has(file) });
}

const stateText = read('docs/state.json');
let state = null;
try {
  state = JSON.parse(stateText);
} catch {
  state = null;
}

const completeness = Math.round((score / required.length) * 100);

console.log('Project Context Kit — notebook check');
console.log('');
console.log(`Project: ${state?.project_name || '(unnamed)'}`);
console.log(`Onboarded: ${state?.onboarded ? 'yes' : 'no'} | Stage: ${state?.stage || 'unknown'}`);
console.log(`Docs present: ${present}/${required.length}`);
console.log(`Completeness: ${completeness}% (${rows.filter((r) => r.status === 'filled').length} filled, ${rows.filter((r) => r.status === 'partial').length} partial, ${rows.filter((r) => r.status === 'empty').length} empty)`);
console.log(`Truth labels: ${totalConfirmed} confirmed, ${totalObserved} observed, ${totalAssumed} assumed, ${totalUnknown} unknown`);
console.log('');

const problems = rows.filter((r) => r.status !== 'filled');
if (problems.length) {
  console.log('Not finished:');
  for (const row of problems) {
    console.log(`- ${row.file} — ${row.status}${row.unknown ? `, ${row.unknown} unknown` : ''}`);
  }
  console.log('');
}

const blockers = [];
for (const file of critical) {
  const row = rows.find((r) => r.file === file);
  if (!row || row.status === 'missing' || row.status === 'empty') {
    blockers.push(`${file} is ${row ? row.status : 'missing'}`);
  }
}
if (!state) blockers.push('docs/state.json is missing or invalid JSON');
if (state && state.handoff_ready !== true) blockers.push('docs/state.json says handoff_ready is not true');
if (!fs.existsSync(path.join(root, '.env.example'))) blockers.push('.env.example is missing (needed to list env var names)');
if (!fs.existsSync(path.join(root, '.git'))) blockers.push('project is not a git repository (history cannot be bundled)');

if (blockers.length) {
  console.log('Handoff blockers:');
  for (const blocker of blockers) console.log(`- ${blocker}`);
} else {
  console.log('Handoff blockers: none. Run the handoff skill.');
}

console.log('');
console.log('Tip: unknown is allowed. Pretending is not. Mark gaps honestly and put the question in OPEN-QUESTIONS.md.');
