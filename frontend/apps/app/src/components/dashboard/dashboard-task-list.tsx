import * as React from "react";

import type { TrainingTask } from "@aioj/api";
import { Tag } from "@aioj/ui";

type DashboardTaskListProps = {
  tasks: TrainingTask[];
};

function resolveTaskTone(status: string) {
  if (status.includes("已完成")) return "success" as const;
  if (status.includes("进行")) return "accent" as const;
  return "default" as const;
}

export function DashboardTaskList({ tasks }: DashboardTaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="rounded-[var(--radius-card)] border border-dashed border-[var(--border-soft)] bg-[var(--surface-muted)] px-5 py-8 text-sm leading-6 text-[var(--text-muted)]">
        当前还没有可展示的训练任务。生成第一份计划后，这里会展示你本周最重要的训练动作。
      </div>
    );
  }

  return (
    <div className="divide-y divide-[var(--border-soft)] overflow-hidden rounded-[var(--radius-card)] border border-[var(--border-soft)] bg-[var(--surface-muted)]">
      {tasks.map((task) => (
        <div key={task.taskId} className="flex items-start justify-between gap-4 px-5 py-4 transition-all duration-300 ease-out hover:bg-[var(--surface-1)]">
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-medium text-[var(--text-primary)]">{task.title}</p>
            <p className="text-sm leading-6 text-[var(--text-muted)]">
              聚焦 {task.focus} · 难度 {task.difficulty}
            </p>
          </div>
          <Tag tone={resolveTaskTone(task.status)}>{task.status}</Tag>
        </div>
      ))}
    </div>
  );
}
