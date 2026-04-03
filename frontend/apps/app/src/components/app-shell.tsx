import * as React from "react";
import type { ReactNode } from "react";
import { BellDot, LogIn, Settings } from "lucide-react";

import { appNav, productTagline } from "@aioj/config";
import { Button } from "@aioj/ui";
import { appPublicPath } from "../lib/paths";
import { ThemeToggle } from "./theme-toggle";

type AppShellProps = {
  title?: string;
  description?: string;
  actions?: ReactNode;
  eyebrow?: string;
  children: ReactNode;
  rail?: ReactNode;
  immersive?: boolean;
  demoMode?: boolean;
};

export function AppShell({ children, rail, immersive, demoMode = false }: AppShellProps) {
  const hasRail = Boolean(rail);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border-soft)] bg-[var(--bg)]/88 backdrop-blur-md">
        <div className={`mx-auto flex h-14 items-center justify-between px-5 md:px-6 ${immersive ? "w-full" : "max-w-[var(--shell-max)]"}`}>
          <a className="flex items-center gap-3 transition-opacity duration-300 ease-out hover:opacity-80" href={appPublicPath("/")}>
            <div className="flex h-8 w-8 items-center justify-center rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] text-[11px] font-semibold tracking-[0.12em] text-[var(--text-primary)]">
              SC
            </div>
            <div>
              <p className="text-[13px] font-semibold leading-tight tracking-[0.02em] text-[var(--text-primary)]">SynCode</p>
              <p className="mt-0.5 text-[10px] uppercase tracking-[0.14em] text-[var(--text-faint)]">{productTagline}</p>
            </div>
          </a>

          <div className="flex items-center gap-1.5">
            <a href={`${appPublicPath("/")}#announcements`}>
              <Button size="sm" variant="ghost">
                <BellDot size={14} className="text-[var(--text-muted)]" />
                <span>公告</span>
              </Button>
            </a>
            <a href={appPublicPath("/settings")}>
              <Button size="sm" variant="ghost">
                <Settings size={14} className="text-[var(--text-muted)]" />
                <span>设置</span>
              </Button>
            </a>
            {demoMode ? (
              <a href={appPublicPath("/login")}>
                <Button size="sm" variant="secondary">
                  <LogIn size={14} className="text-[var(--text-secondary)]" />
                  <span>登录</span>
                </Button>
              </a>
            ) : null}
            <ThemeToggle />
          </div>
        </div>
      </header>

      {demoMode ? (
        <div className="border-b border-[var(--border-soft)] bg-[var(--surface-muted)]">
          <div className={`mx-auto flex items-center justify-between gap-4 px-5 py-3 md:px-6 ${immersive ? "w-full" : "max-w-[var(--shell-max)]"}`}>
            <p className="max-w-4xl text-sm leading-6 text-[var(--text-secondary)]">
              当前查看的是公开体验内容。登录后可以访问个人训练计划、提交记录、考试工作区和 AI 辅助能力。
            </p>
            <a href={appPublicPath("/login")} className="shrink-0">
              <Button size="sm">立即登录</Button>
            </a>
          </div>
        </div>
      ) : null}

      <div className={`mx-auto flex ${immersive ? "w-full" : "max-w-[var(--shell-max)]"}`}>
        {!immersive ? (
          <aside className="hidden w-[240px] shrink-0 border-r border-[var(--border-soft)] xl:block">
            <div className="sticky top-14 px-4 py-6">
              <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">Workspace</p>
              <nav className="space-y-1">
                {appNav.map((item) => (
                  <a
                    key={item.label}
                    className="group flex items-center rounded-[var(--radius-sm)] px-3 py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all duration-300 ease-out hover:bg-[var(--surface-1)] hover:text-[var(--text-primary)]"
                    href={appPublicPath(item.href)}
                  >
                    {item.label}
                  </a>
                ))}
              </nav>
            </div>
          </aside>
        ) : null}

        <main className={`min-w-0 flex-1 ${hasRail && !immersive ? "grid xl:grid-cols-[minmax(0,1fr)_320px]" : ""}`}>
          <div className={immersive ? "h-[calc(100vh-56px)]" : "space-y-8 px-5 py-8 md:px-8 xl:pr-8"}>{children}</div>

          {!immersive && hasRail ? (
            <aside className="hidden border-l border-[var(--border-soft)] xl:block">
              <div className="space-y-5 px-5 py-8">{rail}</div>
            </aside>
          ) : null}
        </main>
      </div>
    </div>
  );
}
