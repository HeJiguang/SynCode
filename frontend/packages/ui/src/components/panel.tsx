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
  accent: "bg-[var(--panel-accent-bg)]"
};

export function Panel({ children, className, hoverable = false, tone = "default", ...props }: PanelProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[12px] border border-[var(--border-soft)]",
        toneClasses[tone],
        "shadow-none transition-colors duration-200 ease-out",
        hoverable && "hover:border-[var(--border-strong)] hover:bg-[var(--surface-3)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
