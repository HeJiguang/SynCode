import * as React from "react";
import type { InputHTMLAttributes } from "react";

import { cn } from "../lib/cn";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--surface-2)] px-3.5 text-sm text-[var(--text-primary)] outline-none transition-colors duration-200 ease-out placeholder:text-[var(--text-muted)] hover:border-[var(--border-focus)] focus:border-[var(--accent)] focus:bg-[var(--surface-3)] focus:ring-0",
        className
      )}
      {...props}
    />
  );
}
