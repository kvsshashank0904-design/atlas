import { IconSpark } from "@/components/icons";

export function AtlasInsight({ text, basis }: { text: string; basis: string }) {
  return (
    <section
      className="animate-fade-up mt-10 flex gap-4 rounded-2xl border border-border bg-surface-2/40 p-6"
      style={{ animationDelay: "260ms" }}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
        <IconSpark className="h-4 w-4" />
      </div>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-accent">
          Atlas noticed
        </p>
        <p className="mt-1.5 text-[15px] leading-relaxed text-foreground/90">
          {text}
        </p>
        <p className="mt-2 text-xs text-muted-2">{basis}</p>
      </div>
    </section>
  );
}
