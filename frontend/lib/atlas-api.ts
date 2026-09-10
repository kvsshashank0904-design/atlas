export type User = { id: string; name: string; email: string };
export type Profile = { id: string; available_time_minutes_per_day: number };
export type Concept = { id: string; name: string; concept_code: string; prerequisite_concept_codes: string[] };
export type Subject = { id: string; name: string; exam_pack: string; chapters: { id: string; name: string; concepts: Concept[] }[] };
export type Diagnostic = { id: string; chapter_id: string; total_questions: number; answered_count: number; remaining_questions: number; status: "in_progress" | "completed" };
export type Question = { question_id: string; question_text: string; question_type: string; difficulty: number; estimated_time_seconds: number };
export type DNA = { concept_id: string; concept_code: string; concept_name: string; accuracy: number; concept_mastery: number; problem_solving_score: number; hint_dependence: number; evidence_count: number; confidence_score: number; last_updated: string };
export type Explanation = { evidence_count: number; correct_count: number; incorrect_count: number; strongest_signal: string | null; weakest_signal: string | null; confidence_explanation: string; question_type_breakdown: { question_type: string; count: number; correct_count: number; accuracy: number }[] };
export class ApiError extends Error { constructor(public status: number, message: string) { super(message); } }
export const tokenKey = "atlas.access_token";
export async function api<T>(path: string, body?: unknown, method?: string): Promise<T> {
  const token = localStorage.getItem(tokenKey);
  const form = body instanceof URLSearchParams;
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: method || (body === undefined ? "GET" : "POST"), cache: "no-store",
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(body !== undefined ? { "Content-Type": form ? "application/x-www-form-urlencoded" : "application/json" } : {}) },
      body: body === undefined ? undefined : form ? body.toString() : JSON.stringify(body),
      signal: AbortSignal.timeout(20000),
    });
  } catch { throw new ApiError(0, "Connection interrupted. Your accepted answers are saved. Check your connection and retry."); }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") {
      localStorage.removeItem(tokenKey); window.dispatchEvent(new Event("atlas:expired"));
    }
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : Array.isArray(detail)
      ? detail.map((e: { loc?: string[]; msg: string }) => `${e.loc?.slice(1).join(" ") || "Input"}: ${e.msg}`).join(". ")
      : detail?.message || "Atlas could not load this request. Please try again.";
    throw new ApiError(response.status, message);
  }
  return data as T;
}
