import * as React from "react";
import type { ReactNode } from "react";

import { adminNav } from "@aioj/config";
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
    <div className="min-h-screen px-4 py-4 md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1600px] gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
        <div className="space-y-4">
          <Panel className="p-5" tone="accent">
            <p className="kicker">Admin Console</p>
            <h1 className="mt-2 text-2xl font-semibold text-white">SynCode Admin</h1>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
              当前登录管理员：{adminName}。管理端保持为独立后台站点，只承担系统配置、内容维护与运营操作。
            </p>
            <form action={adminApiPath("/auth/logout")} method="post" className="mt-4">
              <Button size="sm" variant="secondary">
                退出登录
              </Button>
            </form>
          </Panel>
          <Panel className="p-4">
            <nav className="space-y-2">
              {adminNav.map((item) => (
                <a
                  key={item.label}
                  className="flex items-center justify-between rounded-[18px] border border-transparent px-4 py-3 text-sm text-[var(--text-secondary)] transition hover:border-[var(--border-soft)] hover:bg-white/5 hover:text-[var(--text-primary)]"
                  href={adminPublicPath(item.href)}
                >
                  <span>{item.label}</span>
                  <span className="text-[var(--text-muted)]">/</span>
                </a>
              ))}
            </nav>
          </Panel>
        </div>
        <div className="space-y-4">
          <Panel className="p-6" tone="strong">
            <p className="kicker">Control Plane</p>
            <h2 className="section-title mt-3">{title}</h2>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--text-secondary)]">{description}</p>
          </Panel>
          {children}
        </div>
      </div>
    </div>
  );
}
