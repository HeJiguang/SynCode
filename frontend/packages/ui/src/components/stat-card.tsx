import * as React from "react";
import type { ReactNode } from "react";

import { Panel } from "./panel";
import { cn } from "../lib/cn";

type StatCardProps = {
  label: string;
  value: string;
  detail?: string;
  icon?: ReactNode;
  className?: string;
};

/**
 * StatCard — 数据统计卡片
 * 数字使用 tabular-nums 确保对齐，font-mono 增加几何感。
 */
export function StatCard({ className, detail, icon, label, value }: StatCardProps) {
  return (
    <Panel className={cn("p-5", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-[var(--text-muted)]">
            {label}
          </p>
          <p className="mt-3 font-mono text-3xl font-semibold tabular-nums tracking-tight text-[var(--text-primary)]">
            {value}
          </p>
          {detail ? (
            <p className="mt-1.5 text-xs text-[var(--text-muted)]">{detail}</p>
          ) : null}
        </div>
        {icon ? (
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-2)] text-[var(--text-secondary)]">
            {icon}
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
