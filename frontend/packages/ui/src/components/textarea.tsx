import * as React from "react";
import type { TextareaHTMLAttributes } from "react";

import { cn } from "../lib/cn";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-28 w-full rounded-[var(--radius-sm)] border border-[var(--border-soft)]",
        "bg-[var(--surface-2)] px-3 py-2.5 text-sm text-[var(--text-primary)]",
        "outline-none transition-colors duration-150 resize-none",
        "placeholder:text-[var(--text-muted)]",
        "focus:border-[var(--border-strong)] focus:ring-2 focus:ring-[var(--border-soft)]",
        className
      )}
      {...props}
    />
  );
}
