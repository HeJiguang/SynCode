import * as React from "react";
import type { ReactNode } from "react";
import { LayoutDashboard, LogOut, Shield, Sparkles } from "lucide-react";

import { adminNav, frontendPreviewMode, productName, productTagline } from "@aioj/config";
import { Button, Panel } from "@aioj/ui";

import { adminApiPath, adminPublicPath } from "../lib/paths";

type AdminShellProps = {
  title: string;
  description: string;
  adminName: string;
  children: ReactNode;
};

export function AdminShell({ children, description, title, adminName }: AdminShellProps) {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border-soft)] bg-[var(--surface-overlay)]/92 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[var(--shell-max)] items-center justify-between px-5 md:px-6">
          <a className="flex items-center gap-3 transition-opacity duration-300 ease-out hover:opacity-85" href={adminPublicPath("/")}>
            <div className="flex h-10 w-10 items-center justify-center rounded-[14px] border border-[var(--border-soft)] bg-white text-[12px] font-bold tracking-[0.12em] text-[#071118]">
              SC
            </div>
            <div>
              <p className="text-[14px] font-semibold leading-tight text-[var(--text-primary)]">{productName} 管理后台</p>
              <p className="mt-0.5 text-[10px] uppercase tracking-[0.16em] text-[var(--text-faint)]">{productTagline}</p>
            </div>
          </a>

          <div className="flex items-center gap-2">
            <div className="hidden rounded-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-1 text-[11px] font-semibold tracking-[0.14em] text-[var(--text-secondary)] md:block">
              {frontendPreviewMode ? "预览模式" : "后台模式"}
            </div>
            {frontendPreviewMode ? (
              <a href={adminPublicPath("/questions")}>
                <Button size="sm">
                  <Sparkles size={14} />
                  进入后台预览
                </Button>
              </a>
            ) : (
              <form action={adminApiPath("/auth/logout")} method="post">
                <Button size="sm" variant="secondary">
                  <LogOut size={14} />
                  退出登录
                </Button>
              </form>
            )}
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[var(--shell-max)]">
        <aside className="hidden w-[216px] shrink-0 border-r border-[var(--border-soft)] xl:block">
          <div className="sticky top-16 px-3 py-5">
            <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">后台</p>
            <nav className="space-y-1.5">
              {adminNav.map((item) => (
                <a
                  key={item.label}
                  className="group flex items-center rounded-[14px] border border-transparent px-2 py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all duration-300 ease-out hover:border-[var(--border-soft)] hover:bg-[var(--surface-3)] hover:text-[var(--text-primary)]"
                  href={adminPublicPath(item.href)}
                >
                  <span>{item.label}</span>
                </a>
              ))}
            </nav>

            <Panel className="mt-6 p-4" tone="strong">
              <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                <Shield size={15} />
                <p className="text-sm font-medium">{adminName}</p>
              </div>
              <p className="mt-3 text-xs leading-6 text-[var(--text-muted)]">
                后台只保留配置、内容维护和运营操作，不与用户端页面混在一起。
              </p>
            </Panel>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <div className="space-y-6 px-4 py-6 md:px-6">
            <Panel className="p-5 md:p-6" tone="strong">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div className="max-w-3xl">
                  <p className="kicker">管理控制台</p>
                  <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[var(--text-primary)] md:text-4xl">{title}</h1>
                  <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">{description}</p>
                </div>
                <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                  <LayoutDashboard size={16} />
                  <span>内容、题目、考试与用户管理</span>
                </div>
              </div>
            </Panel>

            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
