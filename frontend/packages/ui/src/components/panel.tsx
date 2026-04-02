import * as React from "react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../lib/cn";

type PanelProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  tone?: "default" | "strong" | "accent";
  hoverable?: boolean;
};

const toneClasses = {
  default: "bg-[var(--surface-1)]/90",
  strong:  "bg-[var(--surface-2)]/92",
  accent:  "bg-[var(--surface-2)]/94"
};

/**
 * Panel — 极致网格与微交互
 * 强制规范卡片，悬停反馈 (hoverable=true)
 */
export function Panel({ children, className, hoverable = false, tone = "default", ...props }: PanelProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[var(--radius-card)] border border-[var(--border-soft)] backdrop-blur-xl",
        "before:pointer-events-none before:absolute before:inset-0 before:bg-[linear-gradient(180deg,rgba(255,255,255,0.06),transparent_28%)] before:opacity-70",
        toneClasses[tone],
        "shadow-[var(--shadow-panel)]",
        hoverable && "transition-all duration-300 cubic-bezier(0.16, 1, 0.3, 1) hover:-translate-y-1 hover:shadow-[var(--shadow-float)] hover:border-[var(--border-strong)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
