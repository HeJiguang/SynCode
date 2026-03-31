import * as React from "react";
import type { ReactNode } from "react";

import { cn } from "../lib/cn";

type TagProps = {
  children: ReactNode;
  tone?: "default" | "accent" | "success" | "warning" | "danger";
  className?: string;
};

/**
 * Tag — 标签
 *
 * Semantic & Delicate Colors.
 * 柔和低保真背景，搭配主题色点缀。
 */
const toneClasses = {
  default: "bg-[var(--surface-2)] text-[var(--text-secondary)]",
  accent:  "bg-[var(--accent-bg)] text-[var(--accent)] font-semibold",
  success: "bg-[var(--success-bg)] text-[var(--success)]",
  warning: "bg-[var(--warning-bg)] text-[var(--warning)]",
  danger:  "bg-[var(--danger-bg)] text-[var(--danger)]"
};

export function Tag({ children, className, tone = "default" }: TagProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-[var(--radius-sm)] border border-transparent",
        "px-2 py-0.5 text-[11px] font-medium tracking-[0.06em] uppercase",
        "transition-colors duration-200",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
