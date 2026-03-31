"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle, Plus } from "lucide-react";

import type { AdminExamDetail } from "../lib/admin-api";
import { adminApiPath, adminInternalPath } from "../lib/paths";
import { Button, Input, Panel, Tag } from "@aioj/ui";

type AdminExamEditorProps = {
  exam?: AdminExamDetail;
};

function toInputValue(value?: string) {
  if (!value) return "";
  return value.replace(" ", "T").slice(0, 16);
}

function toApiValue(value: string) {
  return value ? `${value.replace("T", " ")}:00` : "";
}

export function AdminExamEditor({ exam }: AdminExamEditorProps) {
  const router = useRouter();
  const [form, setForm] = React.useState({
    examId: exam?.examId,
    title: exam?.title ?? "",
    startTime: toInputValue(exam?.startTime),
    endTime: toInputValue(exam?.endTime)
  });
  const [questionIds, setQuestionIds] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(adminApiPath("/exams"), {
        method: exam ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          startTime: toApiValue(form.startTime),
          endTime: toApiValue(form.endTime)
        })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "考试保存失败。");
      }
      router.push(adminInternalPath("/exams"));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "考试保存失败。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!exam?.examId || !window.confirm("确认删除这场考试吗？")) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${adminApiPath("/exams")}?examId=${encodeURIComponent(exam.examId)}`, {
        method: "DELETE"
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "考试删除失败。");
      }
      router.push(adminInternalPath("/exams"));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "考试删除失败。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePublish(publish: boolean) {
    if (!exam?.examId) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(adminApiPath("/exams/publish"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ examId: exam.examId, publish })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "考试状态更新失败。");
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "考试状态更新失败。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAddQuestions() {
    if (!exam?.examId) return;
    const questionIdSet = questionIds
      .split(/[,\s]+/)
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => Number(item))
      .filter((item) => Number.isFinite(item));

    if (questionIdSet.length === 0) {
      setError("请至少输入一个题目 ID。");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(adminApiPath("/exams/questions"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ examId: Number(exam.examId), questionIdSet })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "题目关联失败。");
      }
      setQuestionIds("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "题目关联失败。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemoveQuestion(questionId: string) {
    if (!exam?.examId) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(
        `${adminApiPath("/exams/questions")}?examId=${encodeURIComponent(exam.examId)}&questionId=${encodeURIComponent(questionId)}`,
        { method: "DELETE" }
      );
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "题目移除失败。");
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "题目移除失败。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <Panel className="p-6">
        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="space-y-2 md:col-span-3">
              <span className="text-sm text-[var(--text-secondary)]">考试标题</span>
              <Input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">开始时间</span>
              <Input type="datetime-local" value={form.startTime} onChange={(event) => setForm((current) => ({ ...current, startTime: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">结束时间</span>
              <Input type="datetime-local" value={form.endTime} onChange={(event) => setForm((current) => ({ ...current, endTime: event.target.value }))} />
            </label>
            <div className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">发布状态</span>
              <div className="flex h-11 items-center rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 text-sm text-[var(--text-primary)]">
                {exam?.status === 1 ? "已发布" : "草稿"}
              </div>
            </div>
          </div>

          {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={submitting}>
              {submitting ? <LoaderCircle size={14} className="animate-spin" /> : null}
              保存考试
            </Button>
            {exam ? (
              <>
                <Button type="button" variant="secondary" disabled={submitting} onClick={() => handlePublish(exam.status !== 1)}>
                  {exam.status === 1 ? "撤回发布" : "发布考试"}
                </Button>
                <Button type="button" variant="secondary" disabled={submitting} onClick={handleDelete}>
                  删除考试
                </Button>
              </>
            ) : null}
          </div>
        </form>
      </Panel>

      {exam ? (
        <Panel className="p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="kicker">Question Binding</p>
              <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">关联题目</h3>
            </div>
            <div className="flex w-full max-w-xl gap-3">
              <Input
                placeholder="输入题目 ID，多个用逗号分隔"
                value={questionIds}
                onChange={(event) => setQuestionIds(event.target.value)}
              />
              <Button type="button" onClick={handleAddQuestions} disabled={submitting}>
                <Plus size={14} />
                添加
              </Button>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {exam.examQuestionList.length > 0 ? (
              exam.examQuestionList.map((question) => (
                <div key={question.questionId} className="flex items-center justify-between gap-4 rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)]">{question.title}</p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      {question.questionId} · {question.difficulty}
                    </p>
                  </div>
                  <Button type="button" variant="ghost" onClick={() => handleRemoveQuestion(question.questionId)} disabled={submitting}>
                    移除
                  </Button>
                </div>
              ))
            ) : (
              <div className="rounded-[18px] border border-dashed border-[var(--border-soft)] px-4 py-8 text-sm text-[var(--text-muted)]">
                当前考试还没有关联题目。
              </div>
            )}
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
