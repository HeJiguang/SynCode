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
  strong: "bg-[var(--surface-2)]",
  accent: "bg-[linear-gradient(180deg,rgba(18,24,44,0.95),rgba(12,17,31,0.92))]"
};

export function Panel({ children, className, hoverable = false, tone = "default", ...props }: PanelProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[var(--radius-card)] border border-[var(--border-soft)] backdrop-blur-xl",
        toneClasses[tone],
        "shadow-[var(--shadow-panel)] transition-all duration-300 ease-out",
        hoverable && "hover:-translate-y-0.5 hover:border-[var(--border-strong)] hover:bg-[var(--surface-3)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
