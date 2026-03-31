import * as React from "react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../lib/cn";

type PanelProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  tone?: "default" | "strong" | "accent";
  hoverable?: boolean;
};

const toneClasses = {
  default: "bg-[var(--surface-1)]",
  strong:  "bg-[var(--surface-2)]",
  accent:  "bg-[var(--surface-2)]"
};

/**
 * Panel — 极致网格与微交互
 * 强制规范卡片，悬停反馈 (hoverable=true)
 */
export function Panel({ children, className, hoverable = false, tone = "default", ...props }: PanelProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[var(--radius-card)] border border-[var(--border-soft)]",
        toneClasses[tone],
        hoverable && "transition-all duration-300 cubic-bezier(0.16, 1, 0.3, 1) hover:-translate-y-0.5 hover:shadow-[var(--shadow-float)] hover:border-[var(--border-strong)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
