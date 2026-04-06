"use client";

import * as React from "react";

import type { TrainingTask } from "@aioj/api";
import { Button, Panel, Tag } from "@aioj/ui";

import { appApiPath, appPublicPath } from "../lib/paths";
import { getTrainingStatusLabel, getTrainingStatusTone } from "../lib/presentation";

type TrainingActionsProps = {
  direction: string;
  tasks: TrainingTask[];
};

const TASK_STATUS_PENDING = 0;

function resolveTaskHref(task: TrainingTask) {
  if (task.taskType === "test" && task.examId) {
    return appPublicPath(`/exams/${task.examId}`);
  }
  if (task.questionId) {
    return appPublicPath(`/workspace/${task.questionId}`);
  }
  return null;
}

export function TrainingActions({ direction, tasks }: TrainingActionsProps) {
  const [loadingKey, setLoadingKey] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  async function generatePlan() {
    setLoadingKey("generate");
    setMessage(null);

    try {
      const response = await fetch(appApiPath("/training/generate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ targetDirection: direction || undefined })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "生成训练计划失败。");
      }
      window.location.reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "生成训练计划失败。");
    } finally {
      setLoadingKey(null);
    }
  }

  async function finishTask(taskId: string) {
    setLoadingKey(taskId);
    setMessage(null);

    try {
      const response = await fetch(appApiPath("/training/task/finish"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId, taskStatus: 1 })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "完成任务失败。");
      }
      window.location.reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "完成任务失败。");
    } finally {
      setLoadingKey(null);
    }
  }

  return (
    <Panel className="syncode-page-section p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <h3 className="text-base font-semibold text-[var(--text-primary)]">任务</h3>
        <Button data-testid="training-generate" onClick={() => void generatePlan()} disabled={loadingKey === "generate"}>
          {loadingKey === "generate" ? "生成中..." : "生成计划"}
        </Button>
      </div>

      <div className="mt-4 space-y-3">
        {tasks.map((task) => {
          const href = resolveTaskHref(task);
          return (
            <div key={task.taskId} className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-4 py-4">
              <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_132px] md:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-[var(--text-primary)]">{task.title}</p>
                    <Tag tone={getTrainingStatusTone(task)}>{getTrainingStatusLabel(task)}</Tag>
                  </div>
                  <p className="mt-2 text-xs leading-6 text-[var(--text-muted)]">{task.focus}</p>
                </div>

                <div data-testid={`training-task-actions-${task.taskId}`} className="flex flex-col gap-2 md:w-full md:items-stretch">
                  {href ? (
                    <a
                      href={href}
                      className="inline-flex h-9 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-strong)] bg-[var(--cta-secondary-bg)] px-4 text-sm font-medium text-[var(--text-primary)] transition-all duration-300 ease-out hover:border-[var(--border-focus)] hover:bg-[var(--cta-secondary-hover)] md:w-full"
                    >
                      去做题
                    </a>
                  ) : null}

                  {task.rawStatus === TASK_STATUS_PENDING ? (
                    <Button
                      data-testid={`training-task-finish-${task.taskId}`}
                      variant="secondary"
                      onClick={() => void finishTask(task.taskId)}
                      disabled={loadingKey === task.taskId}
                      className="md:w-full"
                    >
                      {loadingKey === task.taskId ? "提交中..." : "标记完成"}
                    </Button>
                  ) : null}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {message ? <p className="mt-3 text-sm text-[var(--danger)]">{message}</p> : null}
    </Panel>
  );
}
