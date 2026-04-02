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
  default: "border-[var(--border-soft)] bg-[var(--surface-2)]/82 text-[var(--text-secondary)]",
  accent:  "border-transparent bg-[var(--accent-bg)] text-[var(--accent)] font-semibold",
  success: "border-transparent bg-[var(--success-bg)] text-[var(--success)]",
  warning: "border-transparent bg-[var(--warning-bg)] text-[var(--warning)]",
  danger:  "border-transparent bg-[var(--danger-bg)] text-[var(--danger)]"
};

export function Tag({ children, className, tone = "default" }: TagProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border",
        "px-2.5 py-1 text-[11px] font-medium tracking-[0.04em]",
        "transition-colors duration-200",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
