import { Navbar } from "@/components/dashboard/navbar";
import { Hero } from "@/components/dashboard/hero";
import { StudyGpsCard } from "@/components/dashboard/study-gps-card";
import { QuickStats } from "@/components/dashboard/quick-stats";
import { LearningPath } from "@/components/dashboard/learning-path";
import { AtlasInsight } from "@/components/dashboard/atlas-insight";
import { LearningDnaCta } from "@/components/dashboard/learning-dna-cta";
import {
  studentName,
  studyGpsMission,
  quickStats,
  learningPath,
  atlasInsight,
} from "@/lib/mock-data";

export default function DashboardPage() {
  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-6">
        <Hero studentName={studentName} />
        <StudyGpsCard mission={studyGpsMission} />
        <QuickStats stats={quickStats} />
        <LearningPath concepts={learningPath} />
        <AtlasInsight text={atlasInsight.text} basis={atlasInsight.basis} />
        <LearningDnaCta />
      </main>
    </>
  );
}
