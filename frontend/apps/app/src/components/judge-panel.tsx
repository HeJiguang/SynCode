"use client";

import * as React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { SubmissionRecord } from "@aioj/api";

import { buildPendingSubmission, type JudgeResultDetail } from "../lib/judge-result";
import { appApiPath } from "../lib/paths";
import { Tag } from "@aioj/ui";

type JudgePanelProps = {
  questionId: string;
  examId?: string;
  submissions: SubmissionRecord[];
};

type JudgeSubmittedDetail = {
  questionId?: string;
  requestId: string;
  language: string;
};

function toneForStatus(status: SubmissionRecord["status"]) {
  if (status === "Accepted") return "success";
  if (status === "Pending") return "accent";
  if (status === "Wrong Answer") return "warning";
  return "danger";
}

export function JudgePanel({ questionId, examId, submissions }: JudgePanelProps) {
  const [records, setRecords] = useState(submissions);
  const [liveResult, setLiveResult] = useState<JudgeResultDetail | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    setRecords(submissions);
  }, [questionId, submissions]);

  const refreshHistory = useCallback(async () => {
    if (!questionId || !Number.isFinite(Number(questionId))) return;

    setRefreshing(true);
    try {
      const params = new URLSearchParams({ questionId });
      if (examId) params.set("examId", examId);

      const response = await fetch(appApiPath(`/judge/history?${params.toString()}`), {
        cache: "no-store"
      });
      if (!response.ok) return;

      const payload = (await response.json()) as SubmissionRecord[];
      if (Array.isArray(payload) && payload.length > 0) {
        setRecords(payload);
      }
    } finally {
      setRefreshing(false);
    }
  }, [examId, questionId]);

  useEffect(() => {
    const submittedHandler = (event: Event) => {
      const detail = (event as CustomEvent<JudgeSubmittedDetail>).detail;
      if (!detail?.requestId || detail.questionId !== questionId) return;

      setLiveResult({
        questionId,
        requestId: detail.requestId,
        status: "Pending",
        message: "任务已提交，等待判题返回。"
      });
      setRecords((current) => [buildPendingSubmission(detail.requestId, detail.language), ...current].slice(0, 20));
      void refreshHistory();
    };

    const resultHandler = (event: Event) => {
      const detail = (event as CustomEvent<JudgeResultDetail>).detail;
      if (!detail || detail.questionId !== questionId) return;

      setLiveResult(detail);
      void refreshHistory();
    };

    window.addEventListener("syncode:judge-submitted", submittedHandler);
    window.addEventListener("syncode:judge-result", resultHandler);

    return () => {
      window.removeEventListener("syncode:judge-submitted", submittedHandler);
      window.removeEventListener("syncode:judge-result", resultHandler);
    };
  }, [questionId, refreshHistory]);

  const latest = useMemo<SubmissionRecord>(() => {
    if (records[0]) return records[0];
    return {
      submissionId: "--",
      status: liveResult?.status ?? "Pending",
      language: "--",
      runtime: "--",
      memory: "--",
      submittedAt: "--",
      notes: liveResult?.message
    };
  }, [liveResult, records]);

  const displayStatus = liveResult?.status ?? latest.status;
  const displayMessage = liveResult?.message ?? latest.notes;

  return (
    <div className="flex h-full flex-col bg-[var(--surface-1)]">
      <div className="shrink-0 border-b border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="kicker">Judge Result</p>
            <h3 className="mt-0.5 text-base font-semibold text-[var(--text-primary)]">提交结果</h3>
          </div>
          <span className="text-[11px] text-[var(--text-muted)]">{refreshing ? "同步中..." : "实时模式"}</span>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="border-b border-[var(--border-soft)] bg-[var(--surface-2)] px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs text-[var(--text-muted)]">最近一次提交</p>
              <p
                className={`mt-1.5 text-xl font-bold tracking-tight ${
                  displayStatus === "Accepted"
                    ? "text-[var(--success)]"
                    : displayStatus === "Pending"
                      ? "text-[var(--accent)]"
                      : displayStatus === "Wrong Answer"
                        ? "text-[var(--warning)]"
                        : "text-[var(--danger)]"
                }`}
              >
                {displayStatus}
              </p>
            </div>
            <Tag tone={toneForStatus(latest.status)}>{latest.language}</Tag>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-1)] px-3 py-2">
              <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-[var(--text-muted)]">运行时间</p>
              <p className="mt-1 font-mono text-sm tabular-nums text-[var(--text-primary)]">{latest.runtime}</p>
            </div>
            <div className="rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-1)] px-3 py-2">
              <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-[var(--text-muted)]">内存占用</p>
              <p className="mt-1 font-mono text-sm tabular-nums text-[var(--text-primary)]">{latest.memory}</p>
            </div>
          </div>

          {displayMessage ? (
            <div className="mt-3 rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-1)] px-3 py-3">
              <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-[var(--text-muted)]">结果说明</p>
              <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">{displayMessage}</p>
            </div>
          ) : null}

          {liveResult?.failLine ? (
            <div className="mt-3 flex items-center gap-2 rounded-[10px] border border-[var(--danger)]/25 bg-[var(--danger-bg)] px-3 py-2">
              <span className="text-[11px] text-[var(--danger)]">第 {liveResult.failLine} 行附近存在错误或异常。</span>
            </div>
          ) : null}
        </div>

        <div className="divide-y divide-[var(--border-soft)]">
          {records.length > 0 ? (
            records.map((item) => (
              <div key={item.submissionId} className="px-5 py-3 transition-colors hover:bg-[var(--surface-2)]">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-mono text-xs tabular-nums text-[var(--text-muted)]">{item.submissionId}</p>
                  <Tag tone={toneForStatus(item.status)}>{item.status}</Tag>
                </div>
                <p className="mt-1 text-xs text-[var(--text-muted)]">
                  {item.language} · {item.submittedAt}
                </p>
                {item.notes ? <p className="mt-1.5 text-xs leading-5 text-[var(--text-secondary)]">{item.notes}</p> : null}
              </div>
            ))
          ) : (
            <div className="px-5 py-10 text-sm text-[var(--text-muted)]">当前题目还没有真实提交记录。</div>
          )}
        </div>
      </div>
    </div>
  );
}
