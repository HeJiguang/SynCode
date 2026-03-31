import * as React from "react";
import { githubUrl, productName, webNav } from "@aioj/config";
import { SectionShell } from "@aioj/ui";

export function SiteHeader() {
  return (
    <SectionShell className="sticky top-0 z-50 py-4" innerClassName="max-w-7xl">
      <div className="flex items-center justify-between rounded-full border border-[var(--border-soft)] bg-[rgba(11,13,16,0.72)] px-5 py-3 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,var(--accent),var(--accent-cyan))] text-sm font-semibold text-slate-950">
            AI
          </div>
          <div>
            <p className="text-sm font-semibold tracking-[0.18em] text-[var(--text-secondary)]">
              {productName}
            </p>
            <p className="text-xs text-[var(--text-muted)]">Code training with intelligent guidance</p>
          </div>
        </div>
        <nav className="hidden items-center gap-7 text-sm text-[var(--text-secondary)] md:flex">
          {webNav.map((item) => (
            <a
              key={item.label}
              href={item.href}
              rel={item.href === githubUrl ? "noreferrer" : undefined}
              target={item.href === githubUrl ? "_blank" : undefined}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </div>
    </SectionShell>
  );
}
