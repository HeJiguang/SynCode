import * as React from "react";
import type { ReactNode } from "react";
import { BellDot, LogIn, Settings, Sparkles } from "lucide-react";

import { appNav, frontendPreviewLabel, frontendPreviewMode, productName, productTagline } from "@aioj/config";
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
    <div className="syncode-app-shell min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border-soft)] bg-[var(--surface-overlay)]/92 backdrop-blur-xl">
        <div className={`mx-auto flex h-16 items-center justify-between px-5 md:px-6 ${immersive ? "w-full" : "max-w-[var(--shell-max)]"}`}>
          <a className="flex items-center gap-3 transition-opacity duration-300 ease-out hover:opacity-85" href={appPublicPath("/")}>
            <div className="flex h-10 w-10 items-center justify-center rounded-[14px] border border-[var(--border-soft)] bg-white text-[12px] font-bold tracking-[0.12em] text-[#071118]">
              SC
            </div>
            <div>
              <p className="text-[14px] font-semibold leading-tight text-[var(--text-primary)]">{productName}</p>
              <p className="mt-0.5 text-[10px] uppercase tracking-[0.16em] text-[var(--text-faint)]">{productTagline}</p>
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
            {demoMode && !frontendPreviewMode ? (
              <a href={appPublicPath("/login")}>
                <Button size="sm" variant="secondary">
                  <LogIn size={14} className="text-[var(--text-secondary)]" />
                  <span>登录</span>
                </Button>
              </a>
            ) : null}
            {frontendPreviewMode ? (
              <div className="hidden rounded-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--text-secondary)] sm:block">
                {frontendPreviewLabel}
              </div>
            ) : null}
            <ThemeToggle />
          </div>
        </div>
      </header>

      {demoMode ? (
        <div className="border-b border-[var(--border-soft)] bg-[var(--surface-muted)]">
          <div className={`mx-auto flex items-center justify-between gap-4 px-5 py-3 md:px-6 ${immersive ? "w-full" : "max-w-[var(--shell-max)]"}`}>
            <p className="max-w-4xl text-sm leading-7 text-[var(--text-secondary)]">
              {frontendPreviewMode
                ? "当前是前端预览模式：页面已放开登录与后端依赖，方便你直接查看和调整界面。写操作不会真正提交。"
                : "当前展示的是公开体验内容。登录后可以访问个人训练计划、考试工作区、提交记录以及完整的辅助能力。"}
            </p>
            <a href={appPublicPath(frontendPreviewMode ? "/problems" : "/login")} className="shrink-0">
              <Button size="sm">
                <Sparkles size={14} />
                {frontendPreviewMode ? "进入题库预览" : "立即登录"}
              </Button>
            </a>
          </div>
        </div>
      ) : null}

      <div className={`mx-auto flex ${immersive ? "w-full" : "max-w-[var(--shell-max)]"}`}>
        {!immersive ? (
          <aside className="syncode-app-sidebar hidden w-[198px] shrink-0 border-r border-[var(--border-soft)] xl:block">
            <div className="sticky top-16 px-2 py-5">
              <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">Workspace</p>
              <nav className="space-y-1.5">
                {appNav.map((item) => (
                  <a
                    key={item.label}
                    className="group flex items-center rounded-[14px] border border-transparent px-2 py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all duration-300 ease-out hover:border-[var(--border-soft)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]"
                    href={appPublicPath(item.href)}
                  >
                    <span>{item.label}</span>
                  </a>
                ))}
              </nav>
            </div>
          </aside>
        ) : null}

        <main className={`syncode-app-main min-w-0 flex-1 ${hasRail && !immersive ? "grid xl:grid-cols-[minmax(0,1fr)_320px]" : ""}`}>
          <div className={immersive ? "h-[calc(100vh-64px)]" : "syncode-app-content space-y-6 px-4 py-6 md:px-6 xl:pr-6"}>{children}</div>

          {!immersive && hasRail ? (
            <aside className="syncode-app-rail hidden border-l border-[var(--border-soft)] xl:block">
              <div className="space-y-5 px-4 py-6">{rail}</div>
            </aside>
          ) : null}
        </main>
      </div>
    </div>
  );
}
