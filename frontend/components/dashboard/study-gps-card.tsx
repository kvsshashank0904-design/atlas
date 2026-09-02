import { IconArrowRight, IconRoute, IconSpark } from "@/components/icons";
import type { StudyGpsMission } from "@/lib/mock-data";

export function StudyGpsCard({ mission }: { mission: StudyGpsMission }) {
  return (
    <section
      className="animate-fade-up relative mt-8 overflow-hidden rounded-3xl border border-border-strong bg-surface p-6 md:p-10"
      style={{ animationDelay: "80ms" }}
    >
      {/* Ambient glow — decorative only */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-accent-soft blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-24 -left-10 h-56 w-56 rounded-full bg-accent-2/10 blur-3xl"
      />

      <div className="relative flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className="animate-glow-pulse absolute inline-flex h-full w-full rounded-full bg-accent" />
        </span>
        <IconRoute className="h-4 w-4 text-accent" />
        <span className="text-xs font-medium uppercase tracking-[0.2em] text-accent">
          Your Next Mission
        </span>
      </div>

      <h2 className="relative mt-4 text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
        {mission.title}
      </h2>

      <div className="relative mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted">
        <span>{mission.subject}</span>
        <span aria-hidden className="text-muted-2">
          ·
        </span>
        <span>{mission.durationMinutes} min</span>
        <span aria-hidden className="text-muted-2">
          ·
        </span>
        <span>{mission.focusTag}</span>
      </div>

      <p className="relative mt-4 max-w-2xl text-[15px] leading-relaxed text-muted">
        {mission.description}
      </p>

      <div className="relative mt-6 flex gap-3 rounded-2xl border border-border bg-surface-2/60 p-4">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
          <IconSpark className="h-3.5 w-3.5" />
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-accent">
            Why this?
          </p>
          <p className="mt-1 text-sm leading-relaxed text-muted">
            {mission.why}
          </p>
        </div>
      </div>

      <div className="relative mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
        <button
          type="button"
          className="group inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-accent to-accent-2 px-6 py-3 text-sm font-medium text-white transition-transform hover:scale-[1.02] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-offset-2 focus-visible:ring-offset-surface active:scale-[0.99]"
        >
          Continue Mission
          <IconArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </button>
        <button
          type="button"
          className="text-sm text-muted underline-offset-4 transition-colors hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-sm"
        >
          View mission details
        </button>
      </div>
    </section>
  );
}
