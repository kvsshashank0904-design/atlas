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
        {children}
      </body>
    </html>
  );
}
