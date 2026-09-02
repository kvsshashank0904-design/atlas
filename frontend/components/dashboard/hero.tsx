export function Hero({ studentName }: { studentName: string }) {
  return (
    <section className="animate-fade-up pt-10 md:pt-14">
      <p className="text-base text-muted md:text-lg">
        Good evening, {studentName}.
      </p>
      <h1 className="mt-1 text-3xl font-semibold tracking-tight text-foreground md:text-5xl">
        Atlas has your next move.
      </h1>
      <p className="mt-3 max-w-xl text-sm text-muted-2 md:text-base">
        Your learning path is adapting to your progress.
      </p>
    </section>
  );
}
