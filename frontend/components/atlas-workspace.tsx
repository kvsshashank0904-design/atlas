"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError, tokenKey, type User, type Profile, type Subject, type Diagnostic, type Question, type DNA } from "@/lib/atlas-api";
import { Navbar } from "@/components/dashboard/navbar";
import { Hero } from "@/components/dashboard/hero";
import { QuickStats } from "@/components/dashboard/quick-stats";
import { ModelView } from "@/components/model-view";
import { QuestionWorkspace } from "@/components/question-workspace";

type View = "loading" | "auth" | "onboarding" | "dashboard" | "diagnostic";
export function AtlasWorkspace() {
  const [view, setView] = useState<View>("auth");
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [sessions, setSessions] = useState<Diagnostic[]>([]);
  const [dna, setDna] = useState<DNA[]>([]);
  const [session, setSession] = useState<Diagnostic | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [signup, setSignup] = useState(false);
  const operation = useRef(false);
  const epoch = useRef(0);
  const clear = useCallback(() => {
    epoch.current += 1; localStorage.removeItem(tokenKey);
    setUser(null); setProfile(null); setSubjects([]); setSessions([]); setDna([]);
    setSession(null); setQuestion(null); setView("auth"); setError(""); setNotice("");
  }, []);
  const dashboard = useCallback(async () => {
    const current = epoch.current;
    const [u, p, s, d, runs] = await Promise.all([
      api<User>("/auth/me"), api<Profile>("/students/me/profile"), api<Subject[]>("/curriculum/subjects"),
      api<DNA[]>("/learning-dna/me"), api<Diagnostic[]>("/diagnostics/me"),
    ]);
    if (current !== epoch.current) return;
    setUser(u); setProfile(p); setSubjects(s); setDna(d); setSessions(runs); setView("dashboard");
  }, []);
  const bootstrap = useCallback(async () => {
    if (!localStorage.getItem(tokenKey)) { setView("auth"); return; }
    const current = epoch.current;
    const u = await api<User>("/auth/me");
    if (current !== epoch.current) return;
    setUser(u);
    try { await api<Profile>("/students/me/profile"); }
    catch (e) { if (current !== epoch.current) return; if (e instanceof ApiError && e.status === 404) { setView("onboarding"); return; } throw e; }
    if (current === epoch.current) await dashboard();
  }, [dashboard]);
  useEffect(() => {
    const expired = () => { clear(); setNotice("Your session expired. Please log in again."); };
    const storage = (event: StorageEvent) => { if (event.key === tokenKey) { clear(); setNotice("Account changed in another tab. Please log in again."); } };
    window.addEventListener("atlas:expired", expired); window.addEventListener("storage", storage);
    let cancelled = false;
    void Promise.resolve().then(() => { if (!cancelled) return bootstrap(); }).catch(e => { if (!cancelled) { setError(e.message); setView("auth"); } });
    return () => { cancelled = true; window.removeEventListener("atlas:expired", expired); window.removeEventListener("storage", storage); };
  }, [bootstrap, clear]);
  async function run(task: () => Promise<void>) {
    if (operation.current) return;
    operation.current = true; setBusy(true); setError("");
    try { await task(); } catch (e) { setError(e instanceof Error ? e.message : "Please try again."); }
    finally { operation.current = false; setBusy(false); }
  }
  function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    void run(async () => {
      const email = String(form.get("email")).trim(), password = String(form.get("password"));
      if (signup) {
        await api("/auth/signup", { name: String(form.get("name")).trim(), email, password });
        setSignup(false); setNotice("Account created. Signing you in…");
      }
      const token = await api<{ access_token: string }>("/auth/login", new URLSearchParams({ username: email, password }));
      localStorage.setItem(tokenKey, token.access_token); setNotice(""); await bootstrap();
    });
  }
  function onboard(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    void run(async () => {
      await api("/students/onboarding", {
        available_time_minutes_per_day: Number(form.get("minutes")), days_available_per_week: Number(form.get("days")),
        preparation_level: form.get("preparation"), goal: { exam_type: form.get("exam"), target_score: Number(form.get("target")), exam_date: form.get("date") },
      });
      await dashboard();
    });
  }
  async function openDiagnostic(id: string) {
    const current = epoch.current;
    const [status, next] = await Promise.all([api<Diagnostic>(`/diagnostics/${id}`), api<Question | { diagnostic_complete: boolean }>(`/diagnostics/${id}/next`)]);
    if (current !== epoch.current) return;
    if (status.status === "completed") { await dashboard(); return; }
    setSession(status); setQuestion("question_id" in next ? next : null); setView("diagnostic");
  }
  const mechanics = subjects.filter(s => s.exam_pack === "jee").flatMap(s => s.chapters).find(c => c.name === "Mechanics");
  const active = sessions.find(s => s.status === "in_progress" && s.chapter_id === mechanics?.id);
  function start() { void run(async () => {
    if (!mechanics) throw new Error("Mechanics curriculum is not available yet.");
    const runs = await api<Diagnostic[]>("/diagnostics/me");
    const existing = runs.find(s => s.status === "in_progress" && s.chapter_id === mechanics.id);
    const started = existing || await api<Diagnostic>("/diagnostics/start", { chapter_id: mechanics.id });
    await openDiagnostic(started.id);
  }); }
  async function answer(selected: string, confidence: string, seconds: number) {
    if (!session || !question) return;
    await run(async () => {
      try {
        await api(`/diagnostics/${session.id}/answer`, { question_id: question.question_id, selected_answer: selected,
          response_time_seconds: seconds, confidence, hints_used: 0 });
        setNotice("Answer recorded. Learning DNA updates when you complete the diagnostic.");
      } catch (e) {
        // If the response was lost or another tab answered, reconcile with persisted progress.
        const next = await api<Question | { diagnostic_complete: boolean }>(`/diagnostics/${session.id}/next`);
        if ("question_id" in next && next.question_id === question.question_id) throw e;
        setNotice("Recovered your saved progress.");
      }
      await openDiagnostic(session.id);
    });
  }
  const totalEvidence = dna.reduce((sum, state) => sum + state.evidence_count, 0);
  return <>
    <Navbar studentName={user?.name} onHome={() => void run(dashboard)} onModel={() => void run(async () => { await dashboard(); requestAnimationFrame(() => document.getElementById("learning-dna")?.scrollIntoView()); })} onLogout={clear} authenticated={!!user} busy={busy} />
    <main className="atlas-main">
      {error && <div className="message error" role="alert">{error}<button onClick={() => void run(bootstrap)} disabled={busy}>Reload saved state</button></div>}
      {notice && <div className="message" role="status">{notice}</div>}
      {view === "loading" && <div className="panel loading" role="status">Loading your learning state…</div>}
      {view === "auth" && <div className="entry-grid">
        <section className="entry-intro"><p className="eyebrow">ATLAS / LEARNING INTELLIGENCE</p><h1>Understand<br />your <em>next move.</em></h1><p className="intro-copy">Turn your answers into evidence. See what you understand, where to focus, and why.</p><div className="method-strip"><span>01 / OBSERVE</span><span>02 / DIAGNOSE</span><span>03 / UNDERSTAND</span></div><div className="empty-coordinate"><span>YOUR LEARNING STATE</span><p>Waiting for evidence</p><small>Your first diagnostic puts you on the map.</small></div></section>
        <section className="panel entry-form"><p className="eyebrow">YOUR WORKSPACE</p><h2>{signup ? "Create your account" : "Welcome back"}</h2><p className="muted">JEE Physics · Mechanics</p>
          <form onSubmit={authenticate}>
            {signup && <label>Your name<input name="name" required maxLength={120} autoComplete="name" /></label>}
            <label>Email<input name="email" type="email" required autoComplete="email" /></label>
            <label>Password<input name="password" type="password" required minLength={signup ? 8 : 1} maxLength={128} autoComplete={signup ? "new-password" : "current-password"} /></label>
            <button className="primary" disabled={busy}>{busy ? "Connecting…" : signup ? "Create account →" : "Enter workspace →"}</button>
          </form>
          <button className="text-button" disabled={busy} onClick={() => {setSignup(!signup); setError("");}}>{signup ? "Already have an account? Log in" : "New to Atlas? Create an account"}</button>
        </section>
      </div>}
      {view === "onboarding" && <section className="panel onboarding"><p className="eyebrow">01 / CALIBRATE YOUR WORKSPACE</p><h1>A starting point, {user?.name}.</h1><p className="muted">Set your goal. Your diagnostic will measure your current Mechanics understanding.</p><form onSubmit={onboard} className="form-grid">
        <label>Exam<select name="exam"><option value="jee_main">JEE Main</option><option value="jee_advanced">JEE Advanced</option></select></label>
        <label>Target score<input type="number" name="target" min="0" max="360" required placeholder="Your target" /></label>
        <label>Exam date<input type="date" name="date" required /></label>
        <label>Study minutes per day<input type="number" name="minutes" defaultValue={30} min={15} max={960} required /></label>
        <label>Days per week<input type="number" name="days" defaultValue={5} min={1} max={7} required /></label>
        <label>Preparation<select name="preparation"><option value="just_starting">Just starting</option><option value="some_chapters_completed">Some chapters completed</option><option value="most_syllabus_covered">Most syllabus covered</option><option value="revision_phase">Revision</option></select></label>
        <p className="muted wide">Initial curriculum: JEE Physics Mechanics. Content currently covers JEE Main fundamentals.</p>
        <button className="primary wide" disabled={busy}>{busy ? "Saving…" : "Build my workspace →"}</button>
      </form></section>}
      {view === "dashboard" && <>
        <Hero studentName={user?.name || "Student"} />
        <div className="workspace-grid"><section className="panel next-action"><p className="eyebrow">NEXT ACTION / DIAGNOSTIC</p><span className="outline-tag">MECHANICS</span><h2>{active ? "Pick up where you left off." : dna.length ? "Take another measurement." : "Map your starting point."}</h2><p className="muted">{active ? `${active.answered_count} of ${active.total_questions} answers saved. Resume your diagnostic without losing progress.` : "20 questions across concepts, application, strategy, multi-step reasoning, and transfer."}</p><p className="reason">{dna.length ? "Your current model is based on recorded evidence. A new diagnostic adds observations; it does not erase earlier results." : "Atlas needs evidence before it can describe your strengths and gaps. Untested concepts remain unmeasured."}</p><button className="primary" onClick={start} disabled={busy || !mechanics}>{busy ? "Loading…" : active ? "Resume diagnostic →" : "Start diagnostic →"}</button>{!mechanics && <p role="status">Mechanics content is not available. Please check the backend seed.</p>}</section>
        <section className="panel scope"><p className="eyebrow">CURRICULUM / PREREQUISITES</p><h2>Your learning path</h2>{mechanics?.concepts.slice().sort((a,b) => a.prerequisite_concept_codes.length - b.prerequisite_concept_codes.length || a.concept_code.localeCompare(b.concept_code)).map(c => {
          const state = dna.find(d => d.concept_id === c.id);
          return <div className="path-row" key={c.id}><span className={state ? "path-dot measured" : "path-dot"} /><div><strong>{c.name}</strong><small>{c.prerequisite_concept_codes.length ? `Requires: ${c.prerequisite_concept_codes.map(code => mechanics.concepts.find(x => x.concept_code === code)?.name || code).join(", ")}` : "Foundation · no prerequisites"}</small></div><span className="mini-label">{state ? "MEASURED" : "UNMEASURED"}</span></div>;
        })}<p className="muted">Daily study budget: {profile?.available_time_minutes_per_day} minutes</p></section></div>
        <QuickStats stats={[{ label: "Evidence recorded", value: String(totalEvidence), sublabel: "Observations represented in current DNA" }, { label: "Concepts measured", value: `${dna.length} / ${mechanics?.concepts.length || 0}`, sublabel: "Untested concepts are unmeasured" }, { label: "Diagnostics completed", value: String(sessions.filter(s => s.status === "completed").length), sublabel: "From your latest 100 sessions" }]} />
        <ModelView states={dna} />
      </>}
      {view === "diagnostic" && session && <>
        <div className="section-heading"><div><p className="eyebrow">OBSERVE / MECHANICS DIAGNOSTIC</p><h1>One answer. A clearer picture.</h1></div><button className="secondary" disabled={busy} onClick={() => void run(dashboard)}>Save & return</button></div>
        <div className="progress-heading"><span>{session.answered_count} / {session.total_questions} answers saved</span><span>{session.remaining_questions} remaining</span></div><progress value={session.answered_count} max={session.total_questions} aria-label="Diagnostic progress" />
        {question ? <QuestionWorkspace key={question.question_id} question={question} busy={busy} onAnswer={answer} /> : <section className="panel completion"><p className="eyebrow">OBSERVATION COMPLETE</p><h2>Your evidence is ready.</h2><p>Complete the diagnostic to calculate your Learning DNA from the saved answers.</p><button className="primary" disabled={busy} onClick={() => void run(async () => {await api(`/diagnostics/${session.id}/complete`, {}); setNotice("Diagnostic complete. Your learning state has been updated."); await dashboard();})}>{busy ? "Calculating…" : "Complete & view Learning DNA →"}</button></section>}
      </>}
      <footer className="atlas-footer"><span>ATLAS / JEE PHYSICS</span><span>Evidence first. Every measurement counts.</span></footer>
    </main>
  </>;
}
