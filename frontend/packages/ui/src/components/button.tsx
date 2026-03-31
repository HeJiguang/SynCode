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
  /* 极致反差：纯白/纯黑，去渐变发光 */
  primary:
    "bg-[var(--cta-bg)] text-[var(--cta-fg)] hover:bg-[var(--cta-hover)]",
  /* 柔和次级按钮 */
  secondary:
    "border border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text-primary)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)]",
  /* 极简文字按钮 */
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
        "inline-flex items-center justify-center gap-1.5 rounded-[var(--radius-sm)] font-medium",
        // 极致的点击物理反馈
        "transition-transform duration-100 ease-out",
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
