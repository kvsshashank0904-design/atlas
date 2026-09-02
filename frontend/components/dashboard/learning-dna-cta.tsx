import { IconArrowRight } from "@/components/icons";

export function LearningDnaCta() {
  return (
    <section
      className="animate-fade-up mb-16 mt-10 flex flex-col items-start justify-between gap-6 rounded-3xl border border-border-strong bg-gradient-to-br from-surface to-surface-2 p-8 md:flex-row md:items-center"
      style={{ animationDelay: "320ms" }}
    >
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground md:text-2xl">
          See how Atlas sees you.
        </h2>
        <p className="mt-1.5 max-w-md text-sm text-muted">
          Explore the signals behind your progress, strengths, and next steps.
        </p>
      </div>
      <button
        type="button"
        className="group inline-flex shrink-0 items-center gap-2 rounded-full border border-accent/40 px-5 py-2.5 text-sm font-medium text-accent transition-colors hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        Explore Learning DNA
        <IconArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
      </button>
    </section>
  );
}
