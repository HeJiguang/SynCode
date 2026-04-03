import * as React from "react";
import type { ReactNode } from "react";

type DashboardKpiCardProps = {
  label: string;
  value: string;
  detail?: string;
  icon?: ReactNode;
};

export function DashboardKpiCard({ detail, icon, label, value }: DashboardKpiCardProps) {
  return (
    <div className="rounded-[var(--radius-card)] border border-[var(--border-soft)] bg-[var(--surface-1)] p-5 transition-all duration-300 ease-out hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)]">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--text-faint)]">{label}</p>
          <p className="font-mono text-3xl font-semibold tracking-tight text-[var(--text-primary)]">{value}</p>
          {detail ? <p className="text-sm leading-6 text-[var(--text-muted)]">{detail}</p> : null}
        </div>
        {icon ? (
          <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-2)] text-[var(--text-secondary)]">
            {icon}
          </div>
        ) : null}
      </div>
    </div>
  );
}
