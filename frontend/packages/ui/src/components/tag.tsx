import * as React from "react";
import type { ReactNode } from "react";

import { cn } from "../lib/cn";

type TagProps = {
  children: ReactNode;
  tone?: "default" | "accent" | "success" | "warning" | "danger";
  className?: string;
};

const toneClasses = {
  default: "border-[var(--border-soft)] bg-[var(--surface-2)] text-[var(--text-secondary)]",
  accent: "border-transparent bg-[var(--accent-bg)] text-[var(--accent-strong)]",
  success: "border-transparent bg-[var(--success-bg)] text-[var(--success)]",
  warning: "border-transparent bg-[var(--warning-bg)] text-[var(--warning)]",
  danger: "border-transparent bg-[var(--danger-bg)] text-[var(--danger)]"
};

export function Tag({ children, className, tone = "default" }: TagProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-[var(--radius-pill)] border px-2.5 py-1 text-[11px] font-medium tracking-[0.08em] uppercase",
        "transition-colors duration-300 ease-out",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
