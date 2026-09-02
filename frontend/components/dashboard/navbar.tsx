import { IconBell } from "@/components/icons";

const navItems = [
  { label: "Dashboard", href: "#", active: true },
  { label: "Learning DNA", href: "#", active: false },
  { label: "Progress", href: "#", active: false },
];

export function Navbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-2 text-sm font-semibold text-white">
            A
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-[15px] font-semibold tracking-tight text-foreground">
              Atlas
            </span>
            <span className="hidden rounded-full border border-border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted sm:inline-block">
              Learning Companion
            </span>
          </div>
        </div>

        <nav className="hidden items-center gap-1 md:flex">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className={`rounded-full px-3.5 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 ${
                item.active
                  ? "bg-surface-2 text-foreground"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label="Notifications"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-border text-muted transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
          >
            <IconBell className="h-4.5 w-4.5" />
          </button>
          <div
            aria-label="Student avatar"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-sm font-medium text-foreground ring-1 ring-border-strong"
          >
            A
          </div>
        </div>
      </div>
    </header>
  );
}
