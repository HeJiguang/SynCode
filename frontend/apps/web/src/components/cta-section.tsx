import * as React from "react";
import { Button, Panel, SectionShell } from "@aioj/ui";

export function CtaSection() {
  return (
    <SectionShell className="pb-16">
      <Panel className="overflow-hidden p-8 md:p-12">
        <div className="flex flex-col gap-8 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm uppercase tracking-[0.28em] text-[var(--text-muted)]">Ready to Start</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-5xl">开始下一次更高效的编程训练</h2>
            <p className="mt-4 text-base leading-8 text-[var(--text-secondary)]">
              先用公开内容建立第一印象，再进入真实的刷题、训练、考试与 AI 工作流。
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            <a href="/app">
              <Button size="lg">进入 App</Button>
            </a>
            <a href="https://github.com/HeJiguang/SynCode" rel="noreferrer" target="_blank">
              <Button size="lg" variant="secondary">
                查看 GitHub
              </Button>
            </a>
          </div>
        </div>
      </Panel>
    </SectionShell>
  );
}
