import * as React from "react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../lib/cn";

type SectionShellProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
  innerClassName?: string;
};

export function SectionShell({
  children,
  className,
  innerClassName,
  ...props
}: SectionShellProps) {
  return (
    <section className={cn("px-6 py-10 md:px-10 md:py-16", className)} {...props}>
      <div className={cn("mx-auto w-full max-w-7xl", innerClassName)}>{children}</div>
    </section>
  );
}
