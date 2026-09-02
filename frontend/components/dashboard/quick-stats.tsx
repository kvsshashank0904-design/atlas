import type { QuickStat } from "@/lib/mock-data";

export function QuickStats({ stats }: { stats: QuickStat[] }) {
  return (
    <section
      className="animate-fade-up mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3"
      style={{ animationDelay: "140ms" }}
    >
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-2xl border border-border bg-surface p-5 transition-colors hover:border-border-strong"
        >
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            {stat.label}
          </p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
            {stat.value}
          </p>
          <p className="mt-1 text-xs text-muted-2">{stat.sublabel}</p>
        </div>
      ))}
    </section>
  );
}
