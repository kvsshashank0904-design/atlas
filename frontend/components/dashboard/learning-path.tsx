import { IconCheck, IconLock } from "@/components/icons";
import type { PathConcept } from "@/lib/mock-data";

function PathNode({ concept, isLast }: { concept: PathConcept; isLast: boolean }) {
  const { status, name } = concept;

  return (
    <div className="relative flex gap-4 pb-8 last:pb-0">
      {!isLast && (
        <span
          aria-hidden
          className={`absolute left-[15px] top-8 h-[calc(100%-1.5rem)] w-px ${
            status === "completed" ? "bg-accent/40" : "bg-border"
          }`}
        />
      )}

      <div className="relative z-10 shrink-0">
        {status === "completed" && (
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-success/15 text-success ring-1 ring-success/30">
            <IconCheck className="h-4 w-4" />
          </div>
        )}
        {status === "current" && (
          <div className="relative flex h-8 w-8 items-center justify-center">
            <span className="animate-glow-pulse absolute h-8 w-8 rounded-full bg-accent/25" />
            <div className="relative h-3.5 w-3.5 rounded-full bg-accent ring-4 ring-accent-soft" />
          </div>
        )}
        {status === "upcoming" && (
          <div className="flex h-8 w-8 items-center justify-center">
            <div className="h-3 w-3 rounded-full border-2 border-muted-2" />
          </div>
        )}
        {status === "locked" && (
          <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted-2">
            <IconLock className="h-3.5 w-3.5" />
          </div>
        )}
      </div>

      <div className="flex flex-1 items-center justify-between pt-0.5">
        <span
          className={
            status === "current"
              ? "text-lg font-semibold text-foreground"
              : status === "completed"
                ? "text-[15px] text-muted line-through decoration-muted-2/60"
                : status === "upcoming"
                  ? "text-[15px] text-muted"
                  : "text-[15px] text-muted-2"
          }
        >
          {name}
        </span>
        {status === "current" && (
          <span className="rounded-full bg-accent-soft px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-accent">
            Current focus
          </span>
        )}
      </div>
    </div>
  );
}

export function LearningPath({ concepts }: { concepts: PathConcept[] }) {
  return (
    <section
      className="animate-fade-up mt-10"
      style={{ animationDelay: "200ms" }}
    >
      <h2 className="text-xl font-semibold tracking-tight text-foreground">
        Your Learning Path
      </h2>
      <p className="mt-1 text-sm text-muted">
        Mechanics · the route Atlas is building with you
      </p>

      <div className="mt-6 rounded-2xl border border-border bg-surface p-6">
        {concepts.map((concept, index) => (
          <PathNode
            key={concept.id}
            concept={concept}
            isLast={index === concepts.length - 1}
          />
        ))}
      </div>
    </section>
  );
}
