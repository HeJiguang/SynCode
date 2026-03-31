import * as React from "react";
import type { QuestionListItem, TrainingSnapshot } from "@aioj/api";
import { Panel, SectionShell, Tag } from "@aioj/ui";

type WorkflowSectionProps = {
  problem: QuestionListItem;
  training: TrainingSnapshot;
};

const steps = [
  "浏览题目并理解当前训练重点",
  "在工作台内写代码、提交并查看结果",
  "让 AI 结合题面与提交结果给出反馈",
  "把反馈沉淀进训练计划与下一题推荐"
];

export function WorkflowSection({ problem, training }: WorkflowSectionProps) {
  return (
    <SectionShell>
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-5">
          <Tag tone="accent">Training Loop</Tag>
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            把“做题”变成持续迭代的训练工作流
          </h2>
          <p className="max-w-xl text-base leading-8 text-[var(--text-secondary)]">
            首页不堆砌功能截图，而是直接把用户会经历的流程讲清楚。AI OJ 的核心不是题库数量，而是让训练、提交、反馈与计划联动起来。
          </p>
        </div>
        <Panel className="p-6">
          <div className="grid gap-4 md:grid-cols-[1fr_0.88fr]">
            <div className="space-y-4">
              {steps.map((step, index) => (
                <div key={step} className="rounded-[18px] border border-[var(--border-soft)] bg-black/18 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Step 0{index + 1}</p>
                  <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{step}</p>
                </div>
              ))}
            </div>
            <div className="space-y-4">
              <div className="rounded-[18px] border border-[var(--border-soft)] bg-white/4 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Current Focus</p>
                <h3 className="mt-3 text-lg font-semibold">{problem.title}</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">
                  推荐原因：{problem.tags.join(" / ")}，适合作为当前计划的切入题。
                </p>
              </div>
              <div className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--accent-soft)] p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-[#9ecfff]">Training Snapshot</p>
                <h3 className="mt-3 text-lg font-semibold">{training.direction}</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">
                  当前等级 {training.level} · 连续训练 {training.streakDays} 天
                </p>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </SectionShell>
  );
}
