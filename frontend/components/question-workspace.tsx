"use client";
import { useState, type FormEvent } from "react";
import type { Question } from "@/lib/atlas-api";
export function QuestionWorkspace({ question, busy, onAnswer }: { question: Question; busy: boolean; onAnswer: (answer: string, confidence: string, seconds: number) => Promise<void> }) {
  const [answer, setAnswer] = useState("");
  const [confidence, setConfidence] = useState("medium");
  const [started] = useState(() => Date.now());
  function submit(e: FormEvent) { e.preventDefault(); if (!answer.trim()) return; void onAnswer(answer.trim(), confidence, Math.min(7200, Math.max(0, Math.round((Date.now() - started) / 1000)))); }
  const choices = question.question_text.includes("Enter one letter");
  return <div className="question-grid"><section className="panel question-panel"><div className="question-meta"><span>{question.question_type.replaceAll("_", " ")}</span><span>Difficulty {question.difficulty}/5</span><span>~{question.estimated_time_seconds} seconds</span></div><h2>{question.question_text}</h2><form onSubmit={submit}>
    {choices ? <fieldset><legend>Your answer</legend><div className="choice-grid">{["A", "B", "C", "D"].map(letter => <label className={answer === letter ? "choice selected" : "choice"} key={letter}><input type="radio" name="answer" value={letter} checked={answer === letter} onChange={() => setAnswer(letter)} required disabled={busy} /><span>{letter}</span></label>)}</div></fieldset> : <label>Your answer<input value={answer} onChange={e => setAnswer(e.target.value)} required disabled={busy} placeholder="Include the units shown in the question" /></label>}
    <fieldset><legend>How confident are you?</legend><div className="confidence-grid">{["low", "medium", "high"].map(level => <label key={level} className={confidence === level ? "choice selected" : "choice"}><input type="radio" name="confidence" checked={confidence === level} onChange={() => setConfidence(level)} disabled={busy} /><span>{level}</span></label>)}</div></fieldset><button className="primary" disabled={busy || !answer.trim()}>{busy ? "Recording…" : "Submit answer →"}</button></form></section><aside className="panel observation-note"><p className="eyebrow">OBSERVATION NOTES</p><h3>Show your current understanding.</h3><p>Work at your own pace. Confidence is your self-report, separate from the confidence Atlas derives from evidence.</p><hr /><p>Answers are recorded as you go. You can return later. Scores update after explicit completion.</p><p className="muted">This diagnostic measures a starting point. It is not a timed exam.</p></aside></div>;
}
