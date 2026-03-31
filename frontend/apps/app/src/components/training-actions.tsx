"use client";

import * as React from "react";

import type { TrainingTask } from "@aioj/api";
import { Button, Panel } from "@aioj/ui";
import { appApiPath, appPublicPath } from "../lib/paths";

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
        throw new Error(payload?.message ?? "璁粌璁″垝鐢熸垚澶辫触銆?");
      }
      window.location.reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "璁粌璁″垝鐢熸垚澶辫触銆?");
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
        throw new Error(payload?.message ?? "璁粌浠诲姟鏇存柊澶辫触銆?");
      }
      window.location.reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "璁粌浠诲姟鏇存柊澶辫触銆?");
    } finally {
      setLoadingKey(null);
    }
  }

  return (
    <Panel className="p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="kicker">Actions</p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">璁粌鍔ㄤ綔</h3>
        </div>
        <Button data-testid="training-generate" onClick={() => void generatePlan()} disabled={loadingKey === "generate"}>
          {loadingKey === "generate" ? "鐢熸垚涓?.." : "閲嶆柊鐢熸垚璁″垝"}
        </Button>
      </div>

      <div className="mt-5 space-y-3">
        {tasks.map((task) => {
          const href = resolveTaskHref(task);
          return (
            <div key={task.taskId} className="rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-[var(--text-primary)]">{task.title}</p>
                  <p className="mt-1 text-xs text-[var(--text-muted)]">{task.focus}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {href ? (
                    <a
                      href={href}
                      className="inline-flex h-9 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-strong)] bg-[var(--surface-2)] px-4 text-sm font-medium text-[var(--text-primary)]"
                    >
                      杩涘叆浠诲姟
                    </a>
                  ) : null}
                  {task.rawStatus === TASK_STATUS_PENDING ? (
                    <Button
                      data-testid={`training-task-finish-${task.taskId}`}
                      variant="secondary"
                      onClick={() => void finishTask(task.taskId)}
                      disabled={loadingKey === task.taskId}
                    >
                      {loadingKey === task.taskId ? "鎻愪氦涓?.." : "瀹屾垚浠诲姟"}
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
