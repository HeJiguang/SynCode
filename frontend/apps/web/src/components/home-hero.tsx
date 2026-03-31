import * as React from "react";
import type { QuestionListItem, TrainingSnapshot } from "@aioj/api";
import { Button, Panel, SectionShell, Tag } from "@aioj/ui";
import { githubUrl } from "@aioj/config";
type HomeHeroProps = {
  highlightedProblem: QuestionListItem;
  training: TrainingSnapshot;
};

export function HomeHero({ highlightedProblem, training }: HomeHeroProps) {
  return (
    <SectionShell className="pt-8 md:pt-12">
      <div className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-7">
          <Tag tone="accent" className="px-4 py-1.5">
            AI Native Coding Workflow
          </Tag>
          <div className="space-y-5">
            <h1 className="max-w-3xl text-5xl font-semibold leading-tight tracking-tight md:text-7xl">
              让 AI 成为你的编程训练搭档
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-[var(--text-secondary)] md:text-xl">
              一个面向刷题、考试与训练计划的智能工作台，在同一页面完成阅读题面、写代码、提交评测与 AI 复盘。
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            <a href="/app">
              <Button size="lg">开始体验</Button>
            </a>
            <a href={githubUrl} rel="noreferrer" target="_blank">
              <Button size="lg" variant="secondary">
                查看 GitHub
              </Button>
            </a>
          </div>
          <div className="grid gap-4 text-sm text-[var(--text-secondary)] sm:grid-cols-3">
            <div>
              <p className="text-3xl font-semibold text-[var(--text-primary)]">3</p>
              <p className="mt-2">统一覆盖官网、用户端、管理端</p>
            </div>
            <div>
              <p className="text-3xl font-semibold text-[var(--text-primary)]">1</p>
              <p className="mt-2">个工作流内完成做题、提交、问 AI</p>
            </div>
            <div>
              <p className="text-3xl font-semibold text-[var(--text-primary)]">Mock</p>
              <p className="mt-2">先验证产品气质与页面结构</p>
            </div>
          </div>
        </div>
        <div className="relative">
          <div className="absolute -left-12 top-12 h-44 w-44 rounded-full bg-[var(--accent-soft)] blur-3xl" />
          <div className="absolute bottom-0 right-0 h-36 w-36 rounded-full bg-[rgba(69,213,216,0.12)] blur-3xl" />
          <div className="relative grid gap-4">
            <Panel className="hero-card p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Problem Card</p>
                  <h2 className="mt-3 text-xl font-semibold">{highlightedProblem.title}</h2>
                  <p className="mt-2 text-sm text-[var(--text-secondary)]">
                    {highlightedProblem.tags.join(" / ")} · 预计 {highlightedProblem.estimatedMinutes} 分钟
                  </p>
                </div>
                <Tag tone="accent">{highlightedProblem.difficulty}</Tag>
              </div>
              <div className="mt-5 rounded-[18px] border border-[var(--border-soft)] bg-black/25 p-4 text-sm leading-7 text-[var(--text-secondary)]">
                使用哈希表记录已经遍历过的数字，通过补数映射在 O(n) 时间内找到答案。
              </div>
            </Panel>
            <div className="grid gap-4 md:grid-cols-[1.05fr_0.95fr]">
              <Panel className="hero-card p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Editor Focus</p>
                <div className="mt-4 rounded-[18px] border border-[var(--border-soft)] bg-[#0c1117] p-4 font-mono text-sm leading-7 text-[#b8d9ff]">
                  <p>Map&lt;Integer, Integer&gt; seen = new HashMap&lt;&gt;();</p>
                  <p>for (int i = 0; i &lt; nums.length; i++) {"{"}</p>
                  <p className="pl-4">int remain = target - nums[i];</p>
                  <p className="pl-4">if (seen.containsKey(remain)) return ...;</p>
                  <p>{"}"}</p>
                </div>
              </Panel>
              <Panel className="hero-card p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Training Pulse</p>
                <h3 className="mt-3 text-lg font-semibold">{training.title}</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">
                  当前阶段更强调 {training.weaknesses[0]}，并保持 {training.strengths[0]} 的稳定发挥。
                </p>
                <div className="mt-5 rounded-[18px] border border-[var(--border-soft)] bg-white/4 p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-[var(--text-muted)]">AI Suggestion</p>
                  <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
                    先固定「先查后存」模板，再在每次提交后做一段 3 句话复盘。
                  </p>
                </div>
              </Panel>
            </div>
          </div>
        </div>
      </div>
    </SectionShell>
  );
}
