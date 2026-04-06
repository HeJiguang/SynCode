import * as React from "react";
import { ArrowRight, ArrowUpRight, Sparkles } from "lucide-react";

import { githubUrl } from "@aioj/config";
import { Button, Tag } from "@aioj/ui";

const metrics = [
  { value: "1", label: "连续工作面" },
  { value: "3", label: "核心界面" },
  { value: "AI", label: "侧边辅助" }
];

const workspaceLines = [
  "Two Sum",
  "Array / Hash Map / 15 min",
  "Map<Integer, Integer> seen = new HashMap<>();",
  "if (seen.containsKey(remain)) return ...;"
];

export default function HomePage() {
  return (
    <main className="syncode-home-canvas min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
      <section className="px-4 py-4 md:px-8">
        <div className="syncode-home-masthead mx-auto flex max-w-7xl items-center justify-between gap-4 rounded-[18px] border border-[var(--border-soft)] px-4 py-3">
          <a className="flex items-center gap-3 transition-opacity hover:opacity-85" href="/">
            <div className="flex h-9 w-9 items-center justify-center rounded-[12px] border border-[var(--border-soft)] bg-[var(--surface-3)] text-[12px] font-bold tracking-[0.12em] text-[var(--text-primary)]">
              SC
            </div>
            <div>
              <p className="text-sm font-semibold text-[var(--text-primary)]">SynCode</p>
              <p className="text-[11px] text-[var(--text-faint)]">AI 编程训练工作台</p>
            </div>
          </a>

          <div className="flex items-center gap-2">
            <a href="/app">
              <Button size="sm">进入产品</Button>
            </a>
            <a href={githubUrl} rel="noreferrer" target="_blank">
              <Button size="sm" variant="secondary">
                GitHub
              </Button>
            </a>
          </div>
        </div>
      </section>

      <section className="px-4 pb-20 pt-8 md:px-8 md:pt-14">
        <div className="syncode-home-hero mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.84fr_1.16fr]">
          <div className="flex flex-col justify-between gap-8">
            <div className="space-y-5">
              <Tag tone="accent" className="px-3 py-1 text-[10px]">
                AI 编程训练工作台
              </Tag>
              <div className="space-y-4">
                <div className="syncode-home-brandline flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--text-faint)]">
                  <span>Code</span>
                  <span className="h-px w-10 bg-[var(--border-soft)]" />
                  <span>Train</span>
                  <span className="h-px w-10 bg-[var(--border-soft)]" />
                  <span>Judge</span>
                </div>
                <h1 className="max-w-[560px] text-[clamp(3.6rem,6vw,6.8rem)] font-semibold leading-[0.88] tracking-[-0.09em] text-[var(--text-primary)]">
                  SynCode
                </h1>
                <p className="max-w-[460px] text-[18px] leading-8 text-[var(--text-secondary)]">
                  题库、训练、考试、编辑器和 AI，
                  在同一工作面里完成。
                </p>
              </div>
              <div className="flex flex-wrap gap-3 pt-1">
                <a href="/app">
                  <Button className="h-11 px-6 text-[15px]" size="lg">
                    进入产品
                    <ArrowRight size={16} />
                  </Button>
                </a>
                <a href={githubUrl} rel="noreferrer" target="_blank">
                  <Button className="h-11 px-6 text-[15px]" size="lg" variant="secondary">
                    GitHub
                    <ArrowUpRight size={16} />
                  </Button>
                </a>
              </div>
            </div>

            <div className="syncode-home-metric-row grid gap-4 border-t border-[var(--border-soft)] pt-6 sm:grid-cols-3">
              {metrics.map((item) => (
                <div key={item.label} className="syncode-home-metric">
                  <p className="font-mono text-4xl font-semibold tracking-[-0.05em] text-[var(--text-primary)]">{item.value}</p>
                  <p className="mt-2 text-[11px] uppercase tracking-[0.14em] text-[var(--text-faint)]">{item.label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="syncode-home-workbench-wrap">
            <div className="syncode-home-workbench-glow" />
            <div className="syncode-home-workbench rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] p-4 md:p-5">
            <div className="syncode-home-workbench-head mb-4 flex items-center justify-between rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-[#ff6b57]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[#ffcf44]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[var(--accent)]" />
              </div>
              <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">workspace / live</p>
            </div>
            <div className="grid gap-4 xl:grid-cols-[0.98fr_1.06fr]">
              <div className="rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--text-faint)]">Problem</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[var(--text-primary)]">Two Sum</h2>
                    <p className="mt-2 text-sm text-[var(--text-secondary)]">Array / Hash Map / 15 min</p>
                  </div>
                  <Tag tone="success">Easy</Tag>
                </div>

                <div className="mt-5 rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-3)] p-4 text-sm leading-7 text-[var(--text-secondary)]">
                  同一界面里完成读题、写代码、看结果和 AI 辅助。
                </div>
              </div>

              <div className="grid gap-4">
                <div className="rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--text-faint)]">Editor</p>
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-[var(--text-faint)]">
                      <span>Java</span>
                      <span>Run</span>
                    </div>
                  </div>
                  <div className="rounded-[14px] border border-[var(--border-soft)] bg-[#171717] p-4 font-mono text-[13px] leading-7 text-[#d8d8d8]">
                    {workspaceLines.map((line) => (
                      <p key={line} className={line.includes("if (") ? "text-[#4ade80]" : undefined}>
                        {line}
                      </p>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-[0.94fr_1.06fr]">
                  <div className="rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--text-faint)]">Training</p>
                    <p className="mt-3 text-lg font-semibold text-[var(--text-primary)]">训练主线</p>
                  </div>

                  <div className="rounded-[16px] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
                    <div className="flex items-center gap-2">
                      <Sparkles size={15} className="text-[var(--accent)]" />
                      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-strong)]">AI rail</p>
                    </div>
                    <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">侧边辅助</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="syncode-home-workbench-foot mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
                <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">training</p>
                <p className="mt-2 text-sm font-semibold text-[var(--text-primary)]">队列已连接</p>
              </div>
              <div className="rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
                <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">judge</p>
                <p className="mt-2 text-sm font-semibold text-[var(--text-primary)]">结果回流中</p>
              </div>
              <div className="rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
                <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">ai</p>
                <p className="mt-2 text-sm font-semibold text-[var(--text-primary)]">上下文已绑定</p>
              </div>
            </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
