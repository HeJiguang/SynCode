import * as React from "react";
import type { ReactNode } from "react";

import { Panel, Tag } from "@aioj/ui";

type DashboardModuleProps = {
  eyebrow: string;
  title: string;
  description?: string;
  badge?: string;
  children: ReactNode;
  footer?: ReactNode;
  tone?: "default" | "strong" | "accent";
};

export function DashboardModule({
  badge,
  children,
  description,
  eyebrow,
  footer,
  title,
  tone = "default"
}: DashboardModuleProps) {
  return (
    <Panel tone={tone} className="p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="kicker">{eyebrow}</p>
          <div className="space-y-1">
            <h2 className="text-xl font-semibold tracking-[-0.03em] text-[var(--text-primary)]">{title}</h2>
            {description ? <p className="max-w-2xl text-sm leading-6 text-[var(--text-muted)]">{description}</p> : null}
          </div>
        </div>
        {badge ? <Tag tone="accent">{badge}</Tag> : null}
      </div>

      <div className="mt-6">{children}</div>

      {footer ? <div className="mt-6 border-t border-[var(--border-soft)] pt-4">{footer}</div> : null}
    </Panel>
  );
}
