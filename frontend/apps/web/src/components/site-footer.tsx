import * as React from "react";
import { productName, githubUrl } from "@aioj/config";
import { SectionShell } from "@aioj/ui";

export function SiteFooter() {
  return (
    <SectionShell className="py-8">
      <div className="flex flex-col gap-3 border-t border-[var(--border-soft)] pt-6 text-sm text-[var(--text-muted)] md:flex-row md:items-center md:justify-between">
        <p>{productName} · AI 辅助编程训练平台</p>
        <div className="flex flex-wrap gap-5">
          <a href="/app">App</a>
          <a href={githubUrl} rel="noreferrer" target="_blank">
            GitHub
          </a>
        </div>
      </div>
    </SectionShell>
  );
}
