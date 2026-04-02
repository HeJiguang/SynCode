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
  lg: "h-11 px-6 text-base"
};

const variantClasses = {
  primary:
    "bg-[var(--cta-bg)] text-[var(--cta-fg)] shadow-[0_10px_30px_rgba(0,0,0,0.12)] hover:bg-[var(--cta-hover)]",
  secondary:
    "border border-[var(--border-strong)] bg-[var(--surface-2)]/82 text-[var(--text-primary)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)]",
  ghost:
    "text-[var(--text-secondary)] hover:bg-[var(--surface-2)]/72 hover:text-[var(--text-primary)]"
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
        "inline-flex items-center justify-center gap-1.5 rounded-[var(--radius-sm)] font-medium",
        "transition-[transform,background-color,border-color,box-shadow,color] duration-200 ease-out",
        "active:scale-[0.96]", 
        "disabled:cursor-not-allowed disabled:opacity-40 disabled:active:scale-100",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--border-strong)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]",
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
