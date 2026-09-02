import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Atlas — Learning Companion",
  description: "Atlas has your next move.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased dark">
      <body className="relative min-h-full flex flex-col bg-background">
        <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
          <div className="absolute -top-40 left-1/3 h-96 w-96 rounded-full bg-accent/10 blur-[120px]" />
          <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-accent-2/10 blur-[110px]" />
        </div>
        {children}
      </body>
    </html>
  );
}
