"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Icon, type IconName } from "./icon";
import { useWorkspace } from "./workspace";
import { API_BASE } from "@/lib/api";

const links: { href: string; label: string; icon: IconName }[] = [
  { href: "/", label: "Overview", icon: "grid" },
  { href: "/debug", label: "Debug workspace", icon: "bug" },
  { href: "/reproduce", label: "Reproduce bug", icon: "terminal" },
];
export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { health, pending } = useWorkspace();
  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <aside className="sidebar">
      <Link href="/" className="brand"><span className="brand-mark"><Icon name="code" size={23} /></span>PatchPilot<span className="brand-dot">.</span></Link>
      <div className="workspace-label"><span className="workspace-avatar">P</span><div>Personal workspace<small>Local development</small></div></div>
      <p className="nav-caption">WORKSPACE</p>
      <nav aria-label="Main navigation">{links.map((link) => <Link key={link.href} href={link.href} className={`nav-link ${pathname === link.href ? "active" : ""}`} aria-current={pathname === link.href ? "page" : undefined}><Icon name={link.icon} />{link.label}{pathname === link.href && <span className="nav-active-dot" />}</Link>)}</nav>
      <p className="nav-caption resources-caption">RESOURCES</p>
      <a className="nav-link" href={API_BASE + "/docs"} target="_blank" rel="noreferrer"><Icon name="book" />API reference<Icon name="external" size={13} /></a>
      <div className="sidebar-bottom"><div className="isolation-icon"><Icon name="shield" /></div><strong>Evidence over guesswork.</strong><p>Every verified patch is backed by real, isolated test execution.</p><span className="tiny-label">APPROVED PYTHON FIXTURES</span></div>
      <div className="sidebar-footer"><span className={`status-dot ${health?.status === "ok" ? "green" : "neutral"}`} />{health ? health.service : "API not connected"}</div>
    </aside>
    <div className="main-column">
      <header className="topbar"><div className="breadcrumbs">Workspace <span>/</span><strong>{links.find((l) => l.href === pathname)?.label || "PatchPilot"}</strong></div><div className="topbar-right">{pending && <span className="running-label"><span className="spinner" />Execution running</span>}<span className="local-badge"><span className="status-dot green" />LOCAL</span><div className="user-avatar" aria-label="Personal workspace">P</div></div></header>
      <main id="main" tabIndex={-1}>{children}</main>
      <footer className="page-footer"><span>PatchPilot <span className="muted">/</span> Your debugging copilot</span><span>Local workspace · Results are not persisted</span></footer>
    </div>
  </div>;
}
