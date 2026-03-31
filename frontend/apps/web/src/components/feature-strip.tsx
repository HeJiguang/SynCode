import * as React from "react";
import { BrainCircuit, ChartColumnIncreasing, LaptopMinimalCheck } from "lucide-react";

import { Panel, SectionShell } from "@aioj/ui";

const items = [
  {
    title: "AI 辅助讲解",
    description: "在题目上下文内给出思路提示、错误分析与复盘建议。",
    icon: BrainCircuit
  },
  {
    title: "实时评测反馈",
    description: "把提交状态、结果反馈与下一步动作放进同一块工作区。",
    icon: LaptopMinimalCheck
  },
  {
    title: "结构化训练路径",
    description: "用训练画像、任务与阶段测把刷题体验变成长期成长流程。",
    icon: ChartColumnIncreasing
  }
];

export function FeatureStrip() {
  return (
    <SectionShell>
      <div className="grid gap-4 md:grid-cols-3">
        {items.map(({ description, icon: Icon, title }) => (
          <Panel key={title} className="p-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent-cyan)]">
              <Icon size={22} />
            </div>
            <h3 className="mt-6 text-xl font-semibold">{title}</h3>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">{description}</p>
          </Panel>
        ))}
      </div>
    </SectionShell>
  );
}
