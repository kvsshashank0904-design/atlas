export type ConceptStatus = "completed" | "current" | "upcoming" | "locked";

export interface PathConcept {
  id: string;
  name: string;
  status: ConceptStatus;
}

export interface StudyGpsMission {
  title: string;
  subject: string;
  durationMinutes: number;
  focusTag: string;
  description: string;
  why: string;
}

export interface QuickStat {
  label: string;
  value: string;
  sublabel: string;
}

// Mock data only — this file is the single place to swap in real API
// responses once the backend endpoints are wired up.

export const studentName = "Akhil";

export const studyGpsMission: StudyGpsMission = {
  title: "Master Newton's Laws",
  subject: "Physics",
  durationMinutes: 25,
  focusTag: "Multi-step problems",
  description:
    "Strengthen your multi-step problem solving before moving to Friction.",
  why: "Atlas noticed you're strong at identifying forces, but multi-step problems are slowing you down.",
};

export const quickStats: QuickStat[] = [
  {
    label: "Learning DNA",
    value: "72%",
    sublabel: "Overall understanding",
  },
  {
    label: "Streak",
    value: "5 days",
    sublabel: "Keep the momentum",
  },
  {
    label: "Questions solved",
    value: "42",
    sublabel: "Across your path",
  },
];

export const learningPath: PathConcept[] = [
  { id: "vectors", name: "Vectors", status: "completed" },
  { id: "kinematics", name: "Kinematics", status: "completed" },
  { id: "newtons-laws", name: "Newton's Laws", status: "current" },
  { id: "friction", name: "Friction", status: "upcoming" },
  { id: "work-energy", name: "Work & Energy", status: "locked" },
];

export const atlasInsight = {
  text: "Your accuracy is improving, but your confidence drops on unfamiliar multi-step problems.",
  basis: "Based on your recent attempts",
};
