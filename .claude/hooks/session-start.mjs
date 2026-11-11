#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const statePath = path.join(root, 'docs', 'state.json');

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

const state = readJson(statePath, null);
const lines = [];

lines.push('PROJECT CONTEXT KIT — read AGENTS.md and docs/00-START-HERE.md before acting.');

if (!state || state.onboarded !== true) {
  lines.push('STATUS: onboarding is not complete.');
  lines.push('Run the start-here skill now. Interview the owner in plain language, fill the notebook, and confirm the first workflow before scaffolding code.');
  lines.push('First question: What is the business, in one sentence?');
} else {
  lines.push(
    `Project: ${state.project_name || '(unnamed)'} | Stage: ${state.stage || 'unknown'} | Onboarded: yes`
  );
  if (state.current_focus) lines.push(`Current focus: ${state.current_focus}`);
  if (state.next_question) lines.push(`Next question for the owner: ${state.next_question}`);
  lines.push(
    `Open questions: ${state.open_questions ?? '?'} | Assumptions to confirm: ${state.assumptions ?? '?'} | Handoff ready: ${
      state.handoff_ready ? 'yes' : 'no'
    }`
  );
  lines.push(
    'Before coding: run context-interview for any new feature. After coding: run doc-sync. End of session: session entry + state.json.'
  );
}

const logPath = path.join(root, 'docs', '05-SESSIONS', 'SESSION-LOG.md');
try {
  const text = fs.readFileSync(logPath, 'utf8');
  const first = text.search(/^## \d{4}-\d{2}-\d{2}/m);
  if (first !== -1) {
    const rest = text.slice(first);
    const next = rest.slice(1).search(/^## \d{4}-\d{2}-\d{2}/m);
    const entry = next === -1 ? rest : rest.slice(0, next + 1);
    const recent = entry.split('\n').slice(0, 9).join('\n').trim();
    lines.push('');
    lines.push('Most recent session:');
    lines.push(recent);
  }
} catch {
  // no session log yet
}

console.log(lines.join('\n'));
