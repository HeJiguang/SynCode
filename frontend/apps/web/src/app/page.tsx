import * as React from "react";
import { ArrowUpRight, BrainCircuit, ChartColumnIncreasing, LaptopMinimalCheck } from "lucide-react";

import { githubUrl } from "@aioj/config";
import { Button, Panel, Tag } from "@aioj/ui";

const featureCards = [
  {
    icon: <BrainCircuit size={20} />,
    title: "结构化 AI 辅助",
    description: "在题目上下文中直接给出思路引导、错误定位和代码改写建议。"
  },
  {
    icon: <LaptopMinimalCheck size={20} />,
    title: "实时评测闭环",
    description: "写代码、运行、提交、接收结果和复盘都在同一工作区内完成。"
  },
  {
    icon: <ChartColumnIncreasing size={20} />,
    title: "面向成长的训练",
    description: "把热题、阶段目标和训练节奏收拢成一条持续推进的工作流。"
  }
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[var(--bg)]">
      <section className="sticky top-0 z-50 px-4 py-3 md:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between rounded-[var(--radius-card)] nav-bar px-4 py-2.5">
          <a className="flex items-center gap-2.5 transition-opacity hover:opacity-80" href="/">
            <div className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--text-primary)] text-[var(--bg)] text-xs font-bold shadow-sm">
              SC
            </div>
            <div>
              <p className="text-sm font-semibold tracking-[0.1em] text-[var(--text-primary)]">SynCode</p>
              <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">AI 原生编程训练平台</p>
            </div>
          </a>
          <nav className="hidden items-center gap-1.5 md:flex">
            <a href="/app">
              <Button size="sm">开始体验</Button>
            </a>
            <a href={githubUrl} rel="noreferrer" target="_blank">
              <Button size="sm" variant="ghost">
                GitHub
              </Button>
            </a>
          </nav>
        </div>
      </section>

      <section className="px-4 pb-12 pt-16 md:px-8 md:pt-24 lg:pt-32">
        <div className="mx-auto grid max-w-7xl items-start gap-16 lg:grid-cols-[1fr_1fr]">
          <div className="space-y-8">
            <Tag tone="accent" className="bg-[var(--accent-bg)] px-3 py-1 text-[var(--accent)]">
              AI-Native Workflow
            </Tag>
            <div className="space-y-6">
              <h1 className="max-w-xl text-5xl font-extrabold leading-[1.05] tracking-[-0.03em] text-[var(--text-primary)] md:text-[64px]">
                让 AI 成为你的编程训练搭档。
              </h1>
              <p className="max-w-lg text-[17px] leading-relaxed text-[var(--text-secondary)]">
                SynCode 把题库、编辑器、实时判题、训练计划与 AI 辅助收束进同一条工作流，减少切换成本，让练习过程更稳定、更专注。
              </p>
            </div>
            <div className="flex flex-wrap gap-4 pt-2">
              <a href="/app">
                <Button size="lg" className="h-12 px-8 text-[15px] font-semibold" id="hero-cta-primary">
                  进入系统
                </Button>
              </a>
              <a href={githubUrl} rel="noreferrer" target="_blank">
                <Button size="lg" variant="secondary" className="h-12 px-8 text-[15px] font-medium" id="hero-cta-github">
                  GitHub <ArrowUpRight size={16} className="ml-1 opacity-70" />
                </Button>
              </a>
            </div>

            <div className="grid gap-6 border-t border-[var(--border-soft)] pt-8 text-sm sm:grid-cols-3">
              {[
                { num: "1", label: "统一工作区" },
                { num: "3x", label: "更快定位问题" },
                { num: "24/7", label: "随时进入训练" }
              ].map((item) => (
                <div key={item.num} className="group">
                  <p className="font-mono text-3xl font-extrabold tabular-nums text-[var(--text-primary)] transition-colors group-hover:text-[var(--accent)]">
                    {item.num}
                  </p>
                  <p className="mt-1.5 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">{item.label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4">
            <Panel hoverable className="p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="kicker">Problem Setup</p>
                  <h2 className="mt-2 text-xl font-bold text-[var(--text-primary)]">两数之和</h2>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">数组 / 哈希表 / 预计 15 分钟</p>
                </div>
                <Tag tone="success">Easy</Tag>
              </div>
              <div className="mt-5 rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-2)] p-4 text-[13px] leading-6 text-[var(--text-secondary)]">
                题面、代码编辑、运行结果和 AI 分析都保持在一个视口内，避免在多个页面之间来回跳转。
              </div>
            </Panel>

            <div className="grid gap-4 md:grid-cols-[1.02fr_0.98fr]">
              <Panel hoverable className="p-6">
                <p className="kicker">Editor Focus</p>
                <div className="hero-code-block mt-4 p-5 font-mono text-[13px] leading-relaxed text-zinc-300">
                  <p className="text-zinc-500">{"// Find complement"}</p>
                  <p>Map&lt;Integer, Integer&gt; seen = new HashMap&lt;&gt;();</p>
                  <p className="mt-2">for (int i = 0; i &lt; nums.length; i++) {"{"}</p>
                  <p className="pl-4">int rem = target - nums[i];</p>
                  <p className="pl-4 text-cyan-300">if (seen.containsKey(rem)) return ...;</p>
                  <p>{"}"}</p>
                </div>
              </Panel>

              <Panel hoverable className="p-6">
                <p className="kicker">Training Pulse</p>
                <h3 className="mt-2 text-base font-bold text-[var(--text-primary)]">系统联动提示</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                  热题、公告、最近提交和训练目标会自然汇入同一个工作台，而不是分散在多个孤立页面里。
                </p>
                <div className="relative mt-4 overflow-hidden rounded-[var(--radius-sm)] bg-[var(--surface-2)] p-4">
                  <div className="absolute left-0 top-0 h-full w-1 bg-[var(--accent)]" />
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--accent)]">AI Suggestion</p>
                  <p className="text-[13px] leading-relaxed text-[var(--text-secondary)]">
                    当前题目更适合“先查后存”的写法，能够避免索引覆盖带来的边界错误。
                  </p>
                </div>
              </Panel>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-12 border-t border-[var(--border-soft)]/50 px-4 py-16 md:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="mb-12 text-center">
            <p className="kicker text-[var(--accent)]">Core Experience</p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-[var(--text-primary)]">所有关键动作，都在同一条链路里完成</h2>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {featureCards.map((item) => (
              <Panel key={item.title} hoverable className="group relative overflow-hidden p-8">
                <div className="absolute right-0 top-0 p-8 opacity-0 transition-opacity duration-300 group-hover:opacity-[0.03]">
                  {React.cloneElement(item.icon as React.ReactElement<{ size?: number }>, { size: 120 })}
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--surface-2)] text-[var(--text-primary)] transition-transform duration-300 group-hover:scale-110">
                  {item.icon}
                </div>
                <h3 className="mt-6 text-lg font-bold text-[var(--text-primary)]">{item.title}</h3>
                <p className="mt-3 text-[15px] leading-relaxed text-[var(--text-secondary)]">{item.description}</p>
              </Panel>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 pb-20 pt-10 md:px-8">
        <div className="mx-auto max-w-7xl">
          <Panel hoverable className="relative overflow-hidden border-[var(--border-soft)] p-10 md:p-14">
            <div className="pointer-events-none absolute left-1/2 top-1/2 h-full w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--accent)] opacity-[0.03] blur-[100px]" />
            <div className="relative flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-4">
                <Tag tone="accent">Launch Ready</Tag>
                <h2 className="text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">开始下一次更高效的训练。</h2>
                <p className="max-w-xl text-[15px] leading-relaxed text-[var(--text-secondary)]">
                  从公开浏览进入系统，登录后解锁真实判题、AI 对话、训练计划和完整个人工作台。
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-4">
                <a href="/app">
                  <Button size="lg" className="h-14 px-8 text-base shadow-sm" id="cta-banner-primary">
                    进入 SynCode
                  </Button>
                </a>
              </div>
            </div>
          </Panel>

          <div className="mt-12 flex flex-wrap items-center justify-between gap-4 text-[13px] font-medium text-[var(--text-muted)]">
            <p>SynCode · AI Native Coding Trainer</p>
            <div className="flex flex-wrap items-center gap-6">
              <a href="/app" className="transition-colors hover:text-[var(--text-primary)]">
                App
              </a>
              <a
                href={githubUrl}
                rel="noreferrer"
                target="_blank"
                className="transition-colors hover:text-[var(--text-primary)]"
              >
                GitHub
              </a>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
