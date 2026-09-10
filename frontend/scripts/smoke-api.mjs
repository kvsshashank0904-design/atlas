// Writes a fresh test student and 20 answers. Use only a disposable, migrated,
// seeded backend, with a running Next server configured to proxy to that backend.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import ts from 'typescript';
if (process.env.ATLAS_SMOKE_ALLOW_WRITE !== 'yes' || !process.env.ATLAS_SMOKE_BASE_URL) {
  throw new Error('Set ATLAS_SMOKE_ALLOW_WRITE=yes and ATLAS_SMOKE_BASE_URL for a disposable Next/backend environment.');
}
// Browser storage/event adapters only. All HTTP requests, grading and database
// writes use the real application. No backend responses are substituted.
const values = new Map();
globalThis.localStorage = { getItem: k => values.get(k) ?? null, setItem: (k,v) => values.set(k,v), removeItem: k => values.delete(k) };
globalThis.window = new EventTarget();
const realFetch = globalThis.fetch;
globalThis.fetch = (path, options) => realFetch(new URL(path, process.env.ATLAS_SMOKE_BASE_URL), options);
const source = await readFile(new URL('../lib/atlas-api.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { api, tokenKey } = await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'));
const email = `smoke-${randomUUID()}@example.com`, password = randomUUID();
await api('/auth/signup', { name: 'Disposable smoke student', email, password });
await assert.rejects(api('/auth/login', new URLSearchParams({ username: email, password: 'incorrect' })), e => e.status === 401);
const token = await api('/auth/login', new URLSearchParams({ username: email, password }));
localStorage.setItem(tokenKey, token.access_token);
assert.equal((await api('/auth/me')).email, email);
await assert.rejects(api('/students/me/profile'), e => e.status === 404);
await api('/students/onboarding', { available_time_minutes_per_day: 30, days_available_per_week: 5, preparation_level: 'just_starting', goal: { exam_type: 'jee_main', target_score: 180, exam_date: '2027-04-01' } });
const subjects = await api('/curriculum/subjects');
const mechanics = subjects.filter(s => s.exam_pack === 'jee').flatMap(s => s.chapters).find(c => c.name === 'Mechanics');
assert.ok(mechanics);
assert.ok(mechanics.concepts.some(c => c.prerequisite_concept_codes.length > 0));
assert.deepEqual(await api('/learning-dna/me'), []);
const session = await api('/diagnostics/start', { chapter_id: mechanics.id });
assert.equal(session.total_questions, 20);
for (let i = 0; i < 20; i++) {
  const q = await api(`/diagnostics/${session.id}/next`);
  assert.ok(q.question_id); assert.ok(!('answer' in q)); assert.ok(!('solution' in q));
  const body = { question_id: q.question_id, selected_answer: 'A', confidence: 'medium', response_time_seconds: 30, hints_used: 0 };
  const result = await api(`/diagnostics/${session.id}/answer`, body);
  assert.equal(result.remaining_questions, 19 - i);
  await assert.rejects(api(`/diagnostics/${session.id}/answer`, body), e => e.status === 400);
  assert.equal((await api('/diagnostics/me')).find(s => s.id === session.id).answered_count, i + 1);
}
assert.deepEqual(await api('/learning-dna/me'), []);
await api(`/diagnostics/${session.id}/complete`, {});
await api(`/diagnostics/${session.id}/complete`, {});
const states = await api('/learning-dna/me');
assert.equal(states.reduce((sum, s) => sum + s.evidence_count, 0), 20);
for (const state of states) {
  const why = await api(`/learning-dna/me/${state.concept_id}/explanation`);
  assert.equal(why.evidence_count, state.evidence_count);
}
let expired = false;
window.addEventListener('atlas:expired', () => { expired = true; });
localStorage.setItem(tokenKey, 'invalid-token');
await assert.rejects(api('/auth/me'), e => e.status === 401);
assert.equal(localStorage.getItem(tokenKey), null); assert.ok(expired);
console.log('PASS: actual frontend API client → Next proxy → FastAPI → persisted diagnostic/evidence/DNA; retry, resume, expiry.');
