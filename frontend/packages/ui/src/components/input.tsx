import * as React from "react";
import type { InputHTMLAttributes } from "react";

import { cn } from "../lib/cn";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-12 w-full rounded-[14px] border border-[var(--border-soft)] bg-white/[0.03] px-4 text-sm text-[var(--text-primary)] outline-none transition-all duration-300 ease-out placeholder:text-[var(--text-muted)] hover:border-[var(--border-strong)] focus:border-[var(--accent)] focus:ring-0",
        className
      )}
      {...props}
    />
  );
}
