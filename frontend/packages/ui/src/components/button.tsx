import * as React from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "../lib/cn";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
};

const sizeClasses = {
  sm: "h-8 px-3 text-[13px]",
  md: "h-9 px-4 text-sm",
  lg: "h-11 px-5 text-sm"
};

const variantClasses = {
  primary:
    "bg-[var(--cta-bg)] text-[var(--cta-fg)] hover:bg-[var(--cta-hover)]",
  secondary:
    "border border-[var(--border-soft)] bg-[var(--cta-secondary-bg)] text-[var(--text-primary)] hover:border-[var(--border-strong)] hover:bg-[var(--cta-secondary-hover)]",
  ghost:
    "text-[var(--text-secondary)] hover:bg-[var(--cta-secondary-bg)] hover:text-[var(--text-primary)]"
};

export function Button({
  children,
  className,
  size = "md",
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[var(--radius-sm)] font-medium",
        "transition-all duration-300 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--border-focus)] focus-visible:ring-offset-0",
        "active:translate-y-px disabled:cursor-not-allowed disabled:opacity-45 disabled:active:translate-y-0",
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
      type={type}
      {...props}
    >
      {children}
    </button>
  );
}
