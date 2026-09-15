"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp, LoaderCircle, Plus, Save } from "lucide-react";

import { frontendPreviewMode } from "@aioj/config";
import type { AdminExamDetail } from "../lib/admin-api";
import { adminApiPath, adminInternalPath } from "../lib/paths";
import { Button, Input, Panel, Textarea } from "@aioj/ui";

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
    description: exam?.description ?? "",
    startTime: toInputValue(exam?.startTime),
    latestStartTime: toInputValue(exam?.latestStartTime),
    endTime: toInputValue(exam?.endTime),
    durationMinutes: String(exam?.durationMinutes ?? 90),
    timezone: exam?.timezone ?? "Asia/Shanghai",
    maxFormalSubmissions: String(exam?.maxFormalSubmissions ?? 10),
    resultReleasePolicy: exam?.resultReleasePolicy ?? "MANUAL",
    resultReleaseTime: toInputValue(exam?.resultReleaseTime),
    expectedRowVersion: exam?.rowVersion ?? 0
  });
  const [composition, setComposition] = React.useState(() => exam?.examQuestionList.map((item) => ({ ...item })) ?? []);
  const [questionIds, setQuestionIds] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (frontendPreviewMode) {
      setError("当前是前端预览模式，考试改动不会提交到后端。");
      return;
    }
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(adminApiPath("/exams"), {
        method: exam ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          startTime: toApiValue(form.startTime),
          latestStartTime: toApiValue(form.latestStartTime || form.endTime),
          endTime: toApiValue(form.endTime),
          durationMinutes: Number(form.durationMinutes),
          maxFormalSubmissions: Number(form.maxFormalSubmissions),
          resultReleaseTime: form.resultReleaseTime ? toApiValue(form.resultReleaseTime) : null
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
    if (frontendPreviewMode) {
      setError("当前是前端预览模式，删除操作已禁用。");
      return;
    }
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
    if (frontendPreviewMode) {
      setError(`当前是前端预览模式，${publish ? "发布" : "撤回"}操作不会提交到后端。`);
      return;
    }
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

    if (frontendPreviewMode) {
      setError("当前是前端预览模式，题目关联操作不会提交到后端。");
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
    if (frontendPreviewMode) {
      setError(`当前是前端预览模式，题目 ${questionId} 的移除操作已禁用。`);
      return;
    }
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

  async function handleSaveComposition() {
    if (!exam?.examId) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(adminApiPath("/exams/questions"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          examId: exam.examId,
          questions: composition.map((item, index) => ({
            questionId: Number(item.questionId),
            questionOrder: index + 1,
            score: Number(item.score),
            required: item.required
          }))
        })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) throw new Error(payload?.message ?? "组卷保存失败。");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "组卷保存失败。");
    } finally { setSubmitting(false); }
  }

  function moveQuestion(index: number, offset: -1 | 1) {
    setComposition((current) => {
      const target = index + offset;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
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
            <label className="space-y-2 md:col-span-3">
              <span className="text-sm text-[var(--text-secondary)]">考试说明</span>
              <Textarea rows={4} value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">开始时间</span>
              <Input type="datetime-local" value={form.startTime} onChange={(event) => setForm((current) => ({ ...current, startTime: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">最晚入场时间</span>
              <Input type="datetime-local" value={form.latestStartTime} onChange={(event) => setForm((current) => ({ ...current, latestStartTime: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">结束时间</span>
              <Input type="datetime-local" value={form.endTime} onChange={(event) => setForm((current) => ({ ...current, endTime: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">个人作答时长（分钟）</span>
              <Input type="number" min="1" value={form.durationMinutes} onChange={(event) => setForm((current) => ({ ...current, durationMinutes: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">正式提交上限（每题）</span>
              <Input type="number" min="1" value={form.maxFormalSubmissions} onChange={(event) => setForm((current) => ({ ...current, maxFormalSubmissions: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">显示时区</span>
              <Input value={form.timezone} onChange={(event) => setForm((current) => ({ ...current, timezone: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">成绩发布策略</span>
              <select className="h-11 w-full rounded-[8px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 text-sm" value={form.resultReleasePolicy} onChange={(event) => setForm((current) => ({ ...current, resultReleasePolicy: event.target.value }))}><option value="MANUAL">教师手动发布</option><option value="SCHEDULED">定时发布</option></select>
            </label>
            {form.resultReleasePolicy === "SCHEDULED" ? <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">成绩发布时间</span><Input type="datetime-local" value={form.resultReleaseTime} onChange={(event) => setForm((current) => ({ ...current, resultReleaseTime: event.target.value }))} /></label> : null}
            <div className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">发布状态</span>
              <div className="flex h-11 items-center rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 text-sm text-[var(--text-primary)]">
                {exam?.status === 0 ? "草稿" : exam?.status === 1 ? "已发布" : exam?.status === 2 ? "进行中" : exam?.status === 3 ? "已结束" : exam?.status === 4 ? "成绩已发布" : "已取消"}
              </div>
            </div>
          </div>

          {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={submitting || Boolean(exam && exam.status !== 0)}>
              {submitting ? <LoaderCircle size={14} className="animate-spin" /> : null}
              {frontendPreviewMode ? "预览模式下不可保存" : "保存考试"}
            </Button>
            {exam ? (
              <>
                <Button type="button" variant="secondary" disabled={submitting || exam.status > 1} onClick={() => handlePublish(exam.status !== 1)}>
                  {frontendPreviewMode ? "预览模式下不可发布" : exam.status === 1 ? "撤回发布" : "发布考试"}
                </Button>
                <Button type="button" variant="secondary" disabled={submitting || exam.status !== 0} onClick={handleDelete}>
                  {frontendPreviewMode ? "预览模式下不可删除" : "删除考试"}
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
              <Button type="button" onClick={handleAddQuestions} disabled={submitting || exam.status !== 0}>
                <Plus size={14} />
                {frontendPreviewMode ? "预览" : "添加"}
              </Button>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {exam.examQuestionList.length > 0 ? (
              composition.map((question, index) => (
                <div key={question.questionId} className="flex items-center justify-between gap-4 rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)]">{question.title}</p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      {question.questionId} · {question.difficulty} · 第 {index + 1} 题
                    </p>
                  </div>
                  <div className="flex items-center gap-2"><Button type="button" size="sm" variant="ghost" title="上移题目" aria-label="上移题目" onClick={() => moveQuestion(index, -1)} disabled={submitting || exam.status !== 0 || index === 0}><ArrowUp size={14} /></Button><Button type="button" size="sm" variant="ghost" title="下移题目" aria-label="下移题目" onClick={() => moveQuestion(index, 1)} disabled={submitting || exam.status !== 0 || index === composition.length - 1}><ArrowDown size={14} /></Button><label className="flex items-center gap-2 text-xs text-[var(--text-muted)]"><Input className="w-20" type="number" min="1" disabled={exam.status !== 0} value={question.score} onChange={(event) => setComposition((current) => current.map((item) => item.questionId === question.questionId ? { ...item, score: Number(event.target.value) } : item))} />分</label><label className="flex items-center gap-2 text-xs"><input type="checkbox" disabled={exam.status !== 0} checked={question.required} onChange={(event) => setComposition((current) => current.map((item) => item.questionId === question.questionId ? { ...item, required: event.target.checked } : item))} />必答</label><Button type="button" variant="ghost" onClick={() => handleRemoveQuestion(question.questionId)} disabled={submitting || exam.status !== 0}>{frontendPreviewMode ? "预览" : "移除"}</Button></div>
                </div>
              ))
            ) : (
              <div className="rounded-[18px] border border-dashed border-[var(--border-soft)] px-4 py-8 text-sm text-[var(--text-muted)]">
                当前考试还没有关联题目。
              </div>
            )}
          </div>
          {composition.length ? <div className="mt-4 flex items-center justify-between border-t border-[var(--border-soft)] pt-4"><p className="text-sm text-[var(--text-secondary)]">总分 {composition.reduce((sum, item) => sum + Number(item.score || 0), 0)}</p><Button type="button" variant="secondary" onClick={() => void handleSaveComposition()} disabled={submitting || exam.status !== 0}><Save size={14} />保存题序与配分</Button></div> : null}
        </Panel>
      ) : null}
    </div>
  );
}
