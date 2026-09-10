"use client";
import Link from "next/link";
export function Navbar({ studentName, authenticated = false, onHome, onModel, onLogout, busy = false }: { studentName?: string; authenticated?: boolean; onHome?: () => void; onModel?: () => void; onLogout?: () => void; busy?: boolean }) {
  return <header className="atlas-nav"><Link href="/" className="atlas-brand" aria-label="Atlas home"><span className="brand-mark">A</span><span>ATLAS<small>LEARNING INTELLIGENCE</small></span></Link>{authenticated && <nav aria-label="Main navigation"><button onClick={onHome} disabled={busy}>Workspace</button><button onClick={onModel} disabled={busy}>Learning DNA</button></nav>}<div className="nav-account">{studentName && <span>{studentName}</span>}{authenticated && <button onClick={onLogout}>Log out</button>}</div></header>;
}
