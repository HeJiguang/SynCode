import * as React from "react";
import type { ReactNode } from "react";

import { cn } from "../lib/cn";

type MetricPillProps = {
  label: string;
  value: string;
  icon?: ReactNode;
  className?: string;
};

export function MetricPill({ className, icon, label, value }: MetricPillProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-full border border-[var(--border-soft)] bg-black/24 px-4 py-3 text-sm text-[var(--text-secondary)]",
        className
      )}
    >
      {icon ? (
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent-cyan)]">
          {icon}
        </span>
      ) : null}
      <span className="flex flex-col">
        <span className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">{label}</span>
        <span className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{value}</span>
      </span>
    </div>
  );
}
