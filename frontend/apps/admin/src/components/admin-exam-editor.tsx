"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp, LoaderCircle, Plus, Save, Search } from "lucide-react";

import { frontendPreviewMode } from "@aioj/config";
import { utcDateTimeToZonedInput } from "@aioj/api";
import type { AdminExamDetail } from "../lib/admin-api";
import { buildExamCompositionPayload, type ExamFormErrors, type ExamFormValues, toExamApiDateTime, validateExamForm } from "../lib/exam-form";
import { adminApiPath, adminInternalPath } from "../lib/paths";
import { Button, Input, Panel, Textarea } from "@aioj/ui";

type AdminExamEditorProps = {
  exam?: AdminExamDetail;
};

type SearchQuestion = { questionId: string; title: string; difficulty: number; questionType: string };

const typeLabels: Record<string, string> = {
  PROGRAMMING: "编程题", SINGLE_CHOICE: "单选题", MULTIPLE_CHOICE: "多选题", TRUE_FALSE: "判断题",
  FILL_BLANK: "填空题", SHORT_ANSWER: "简答题", SQL: "SQL 题", FILE: "文件题", PROJECT: "项目题"
};

function toInputValue(value: string | undefined, timezone: string) {
  if (!value) return "";
  if (!frontendPreviewMode) return utcDateTimeToZonedInput(value, timezone);
  return value.replace(" ", "T").slice(0, 16);
}

export function AdminExamEditor({ exam }: AdminExamEditorProps) {
  const router = useRouter();
  const initialTimezone = exam?.timezone ?? "Asia/Shanghai";
  const [form, setForm] = React.useState({
    examId: exam?.examId,
    title: exam?.title ?? "",
    description: exam?.description ?? "",
    startTime: toInputValue(exam?.startTime, initialTimezone),
    latestStartTime: toInputValue(exam?.latestStartTime, initialTimezone),
    endTime: toInputValue(exam?.endTime, initialTimezone),
    durationMinutes: String(exam?.durationMinutes ?? 90),
    timezone: initialTimezone,
    maxFormalSubmissions: String(exam?.maxFormalSubmissions ?? 10),
    resultReleasePolicy: exam?.resultReleasePolicy ?? "MANUAL",
    resultReleaseTime: toInputValue(exam?.resultReleaseTime, initialTimezone),
    expectedRowVersion: exam?.rowVersion ?? 0
  });
  const [composition, setComposition] = React.useState(() => exam?.examQuestionList.map((item) => ({ ...item })) ?? []);
  const [questionQuery, setQuestionQuery] = React.useState("");
  const [questionType, setQuestionType] = React.useState("");
  const [searchResults, setSearchResults] = React.useState<SearchQuestion[]>([]);
  const [searching, setSearching] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = React.useState<ExamFormErrors>({});

  React.useEffect(() => {
    if (exam) {
      setForm((current) => ({ ...current, expectedRowVersion: exam.rowVersion }));
    }
  }, [exam?.rowVersion]);

  function updateField<K extends keyof ExamFormValues>(key: K, value: ExamFormValues[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setFieldErrors((current) => ({ ...current, [key]: undefined }));
    setNotice(null);
  }

  function applyViolations(details: unknown) {
    if (!details || typeof details !== "object") return false;
    const violations = (details as { violations?: unknown }).violations;
    if (!Array.isArray(violations)) return false;
    const next: ExamFormErrors = {};
    for (const violation of violations) {
      if (!violation || typeof violation !== "object") continue;
      const { field, message } = violation as { field?: unknown; message?: unknown };
      if (typeof field === "string" && typeof message === "string" && field in form) {
        next[field as keyof ExamFormValues] = message;
      }
    }
    setFieldErrors(next);
    return Object.keys(next).length > 0;
  }

  React.useEffect(() => {
    if (!exam || exam.status !== 0 || frontendPreviewMode) return;
    const timer = window.setTimeout(async () => {
      setSearching(true);
      try {
        const query = new URLSearchParams();
        if (questionQuery.trim()) query.set("title", questionQuery.trim());
        if (questionType) query.set("questionType", questionType);
        const response = await fetch(`${adminApiPath("/questions")}?${query}`);
        const payload = await response.json() as { message?: string; rows?: Array<{ questionId: string | number; title: string; difficulty: number; questionType?: string }> };
        if (!response.ok) throw new Error(payload.message ?? "题库加载失败。");
        setSearchResults((payload.rows ?? []).map((item) => ({ ...item, questionId: String(item.questionId), questionType: item.questionType ?? "PROGRAMMING" })));
      } catch (searchError) {
        setError(searchError instanceof Error ? searchError.message : "题库加载失败。");
      } finally { setSearching(false); }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [exam, questionQuery, questionType]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (frontendPreviewMode) {
      setError("当前是前端预览模式，考试改动不会提交到后端。");
      return;
    }
    const nextFieldErrors = validateExamForm(form);
    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors);
      setError("请先修正标出的考试信息。");
      const firstField = Object.keys(nextFieldErrors)[0];
      window.requestAnimationFrame(() => document.querySelector<HTMLElement>(`[name="${firstField}"]`)?.focus());
      return;
    }
    setSubmitting(true);
    setError(null);
    setNotice(null);

    try {
      const response = await fetch(adminApiPath("/exams"), {
        method: exam ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          title: form.title.trim(),
          startTime: toExamApiDateTime(form.startTime, form.timezone),
          latestStartTime: toExamApiDateTime(form.latestStartTime, form.timezone),
          endTime: toExamApiDateTime(form.endTime, form.timezone),
          durationMinutes: Number(form.durationMinutes),
          maxFormalSubmissions: Number(form.maxFormalSubmissions),
          resultReleaseTime: form.resultReleaseTime ? toExamApiDateTime(form.resultReleaseTime, form.timezone) : null
        })
      });
      const payload = (await response.json().catch(() => null)) as { examId?: string; message?: string; details?: unknown } | null;
      if (!response.ok) {
        if (applyViolations(payload?.details)) throw new Error("请先修正标出的考试信息。");
        throw new Error(payload?.message ?? "考试保存失败。");
      }
      if (!exam && payload?.examId) {
        router.push(adminInternalPath(`/exams/${payload.examId}`));
      } else {
        setNotice("考试信息已保存。");
        router.refresh();
      }
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
    setNotice(null);
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
    setNotice(null);
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
      setNotice(publish ? "考试已发布。" : "考试已撤回为草稿。");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "考试状态更新失败。");
    } finally {
      setSubmitting(false);
    }
  }

  function addQuestion(question: SearchQuestion) {
    setComposition((current) => current.some((item) => item.questionId === question.questionId) ? current : [...current, {
      questionId: question.questionId, title: question.title,
      difficulty: question.difficulty === 1 ? "Easy" : question.difficulty === 3 ? "Hard" : "Medium",
      questionOrder: current.length + 1, score: question.questionType === "PROGRAMMING" ? 30 : 10,
      required: true, questionType: question.questionType
    }]);
  }

  async function handleSaveComposition() {
    if (!exam?.examId) return;
    if (composition.some((item) => !Number.isFinite(Number(item.score)) || Number(item.score) <= 0)) {
      setError("每道题的分值必须大于 0。");
      return;
    }
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(adminApiPath("/exams/questions"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          examId: exam.examId,
          questions: buildExamCompositionPayload(composition)
        })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) throw new Error(payload?.message ?? "组卷保存失败。");
      setNotice("题序与配分已保存。");
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
        <form className="space-y-5" onSubmit={handleSubmit} noValidate>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="space-y-2 md:col-span-3">
              <span className="text-sm text-[var(--text-secondary)]">考试标题</span>
              <Input name="title" required aria-invalid={Boolean(fieldErrors.title)} aria-describedby={fieldErrors.title ? "title-error" : undefined} value={form.title} onChange={(event) => updateField("title", event.target.value)} />
              {fieldErrors.title ? <span id="title-error" className="block text-xs text-[var(--danger)]">{fieldErrors.title}</span> : null}
            </label>
            <label className="space-y-2 md:col-span-3">
              <span className="text-sm text-[var(--text-secondary)]">考试说明</span>
              <Textarea rows={4} value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">开始时间</span>
              <Input name="startTime" required type="datetime-local" aria-invalid={Boolean(fieldErrors.startTime)} value={form.startTime} onInput={(event) => updateField("startTime", event.currentTarget.value)} />
              {fieldErrors.startTime ? <span className="block text-xs text-[var(--danger)]">{fieldErrors.startTime}</span> : null}
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">最晚入场时间</span>
              <Input name="latestStartTime" required type="datetime-local" aria-invalid={Boolean(fieldErrors.latestStartTime)} value={form.latestStartTime} onInput={(event) => updateField("latestStartTime", event.currentTarget.value)} />
              {fieldErrors.latestStartTime ? <span className="block text-xs text-[var(--danger)]">{fieldErrors.latestStartTime}</span> : null}
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">结束时间</span>
              <Input name="endTime" required type="datetime-local" aria-invalid={Boolean(fieldErrors.endTime)} value={form.endTime} onInput={(event) => updateField("endTime", event.currentTarget.value)} />
              {fieldErrors.endTime ? <span className="block text-xs text-[var(--danger)]">{fieldErrors.endTime}</span> : null}
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">个人作答时长（分钟）</span>
              <Input name="durationMinutes" required type="number" min="1" step="1" aria-invalid={Boolean(fieldErrors.durationMinutes)} value={form.durationMinutes} onChange={(event) => updateField("durationMinutes", event.target.value)} />
              {fieldErrors.durationMinutes ? <span className="block text-xs text-[var(--danger)]">{fieldErrors.durationMinutes}</span> : null}
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">正式提交上限（每题）</span>
              <Input name="maxFormalSubmissions" required type="number" min="1" step="1" aria-invalid={Boolean(fieldErrors.maxFormalSubmissions)} value={form.maxFormalSubmissions} onChange={(event) => updateField("maxFormalSubmissions", event.target.value)} />
              {fieldErrors.maxFormalSubmissions ? <span className="block text-xs text-[var(--danger)]">{fieldErrors.maxFormalSubmissions}</span> : null}
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">显示时区</span>
              <Input name="timezone" required aria-invalid={Boolean(fieldErrors.timezone)} value={form.timezone} onChange={(event) => updateField("timezone", event.target.value)} />
              {fieldErrors.timezone ? <span className="block text-xs text-[var(--danger)]">{fieldErrors.timezone}</span> : null}
            </label>
            <label className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">成绩发布策略</span>
              <select name="resultReleasePolicy" className="h-11 w-full rounded-[8px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 text-sm" value={form.resultReleasePolicy} onChange={(event) => updateField("resultReleasePolicy", event.target.value)}><option value="MANUAL">教师手动发布</option><option value="SCHEDULED">定时发布</option></select>
            </label>
            {form.resultReleasePolicy === "SCHEDULED" ? <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">成绩发布时间</span><Input name="resultReleaseTime" required type="datetime-local" aria-invalid={Boolean(fieldErrors.resultReleaseTime)} value={form.resultReleaseTime} onInput={(event) => updateField("resultReleaseTime", event.currentTarget.value)} />{fieldErrors.resultReleaseTime ? <span className="block text-xs text-[var(--danger)]">{fieldErrors.resultReleaseTime}</span> : null}</label> : null}
            <div className="space-y-2">
              <span className="text-sm text-[var(--text-secondary)]">发布状态</span>
              <div className="flex h-11 items-center rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 text-sm text-[var(--text-primary)]">
                {!exam || exam.status === 0 ? "草稿" : exam.status === 1 ? "已发布" : exam.status === 2 ? "进行中" : exam.status === 3 ? "已结束" : exam.status === 4 ? "成绩已发布" : "已取消"}
              </div>
            </div>
          </div>

          {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
          {notice ? <p className="text-sm text-[var(--success)]" role="status">{notice}</p> : null}

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
          <div className="space-y-4">
            <div>
              <p className="kicker">试卷题目</p>
              <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">搜索并组卷</h3>
            </div>
            {exam.status === 0 ? <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px]">
              <div className="relative"><Search size={16} className="pointer-events-none absolute left-3 top-3.5 text-[var(--text-muted)]" /><Input className="pl-10" placeholder="按标题搜索题库" value={questionQuery} onChange={(event) => setQuestionQuery(event.target.value)} /></div>
              <select className="h-11 rounded-[8px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 text-sm" value={questionType} onChange={(event) => setQuestionType(event.target.value)}><option value="">全部题型</option>{Object.entries(typeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
            </div>
            : null}
            {exam.status === 0 ? <div className="max-h-64 overflow-y-auto border-y border-[var(--border-soft)]">
              {searching ? <p className="py-5 text-sm text-[var(--text-muted)]">正在搜索...</p> : searchResults.map((item) => {
                const added = composition.some((question) => question.questionId === item.questionId);
                return <div key={item.questionId} className="grid grid-cols-[1fr_auto] items-center gap-3 border-b border-[var(--border-soft)] py-3 last:border-0"><div><p className="text-sm font-medium">{item.title}</p><p className="mt-1 text-xs text-[var(--text-muted)]">{typeLabels[item.questionType] ?? item.questionType} · #{item.questionId}</p></div><Button type="button" size="sm" variant="ghost" disabled={added} onClick={() => addQuestion(item)}><Plus size={14} />{added ? "已加入" : "加入"}</Button></div>;
              })}
            </div> : null}
          </div>

          <div className="mt-5 space-y-3">
            {composition.length > 0 ? (
              composition.map((question, index) => (
                <div key={question.questionId} className="flex items-center justify-between gap-4 rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)]">{question.title}</p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      {question.questionId} · {typeLabels[question.questionType] ?? question.questionType} · {question.difficulty} · 第 {index + 1} 题
                    </p>
                  </div>
                  <div className="flex items-center gap-2"><Button type="button" size="sm" variant="ghost" title="上移题目" aria-label="上移题目" onClick={() => moveQuestion(index, -1)} disabled={submitting || exam.status !== 0 || index === 0}><ArrowUp size={14} /></Button><Button type="button" size="sm" variant="ghost" title="下移题目" aria-label="下移题目" onClick={() => moveQuestion(index, 1)} disabled={submitting || exam.status !== 0 || index === composition.length - 1}><ArrowDown size={14} /></Button><label className="flex items-center gap-2 text-xs text-[var(--text-muted)]"><Input className="w-20" type="number" min="1" disabled={exam.status !== 0} value={question.score} onChange={(event) => setComposition((current) => current.map((item) => item.questionId === question.questionId ? { ...item, score: Number(event.target.value) } : item))} />分</label><label className="flex items-center gap-2 text-xs"><input type="checkbox" disabled={exam.status !== 0} checked={question.required} onChange={(event) => setComposition((current) => current.map((item) => item.questionId === question.questionId ? { ...item, required: event.target.checked } : item))} />必答</label><Button type="button" variant="ghost" onClick={() => setComposition((current) => current.filter((item) => item.questionId !== question.questionId))} disabled={submitting || exam.status !== 0}>{frontendPreviewMode ? "预览" : "移除"}</Button></div>
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
