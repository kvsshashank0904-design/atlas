export function Hero({ studentName }: { studentName: string }) {
  return <section className="dashboard-hero"><p className="eyebrow">YOUR LEARNING WORKSPACE</p><h1>Welcome, <em>{studentName}.</em></h1><p>Observe the evidence. Understand your starting point.</p></section>;
}
