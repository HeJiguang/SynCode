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
    "border border-[var(--border-focus)] bg-[var(--accent)] text-white shadow-none hover:border-[var(--accent-strong)] hover:bg-[var(--accent-strong)]",
  secondary:
    "border border-[var(--border-strong)] bg-[var(--cta-secondary-bg)] text-[var(--text-primary)] hover:border-[var(--border-focus)] hover:bg-[var(--cta-secondary-hover)]",
  ghost:
    "text-[var(--text-secondary)] hover:bg-[var(--surface-2)] hover:text-[var(--text-primary)]"
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
        "inline-flex items-center justify-center gap-2 rounded-[8px] font-medium",
        "transition-colors duration-200 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--border-focus)] focus-visible:ring-offset-0",
        "active:translate-y-px disabled:cursor-not-allowed disabled:border-[rgba(120,136,182,0.28)] disabled:bg-[rgba(120,136,182,0.2)] disabled:text-[color:color-mix(in_srgb,var(--text-primary)_68%,transparent)] disabled:shadow-none disabled:active:translate-y-0",
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
