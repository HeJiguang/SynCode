"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle, Plus, Trash2 } from "lucide-react";

import { frontendPreviewMode } from "@aioj/config";
import type { AdminQuestionDetail } from "../lib/admin-api";
import { adminApiPath, adminInternalPath } from "../lib/paths";
import { Button, Input, Panel, Textarea } from "@aioj/ui";

type AdminQuestionEditorProps = { question?: AdminQuestionDetail };
type Option = { id: string; label: string };

const questionTypes = [
  ["PROGRAMMING", "编程题"], ["SINGLE_CHOICE", "单选题"], ["MULTIPLE_CHOICE", "多选题"],
  ["TRUE_FALSE", "判断题"], ["FILL_BLANK", "填空题"], ["SHORT_ANSWER", "简答题"],
  ["SQL", "SQL 题"], ["FILE", "文件题"], ["PROJECT", "项目题"]
] as const;

const selectClassName =
  "h-11 rounded-[8px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--border-strong)]";

function parseJson(value: string) {
  try { return JSON.parse(value) as Record<string, unknown>; } catch { return {}; }
}

function initialOptions(question?: AdminQuestionDetail): Option[] {
  const value = parseJson(question?.answerConfigJson ?? "{}").options;
  return Array.isArray(value) && value.length
    ? value.map((item, index) => ({
        id: String((item as { id?: string }).id ?? String.fromCharCode(65 + index)),
        label: String((item as { label?: string }).label ?? "")
      }))
    : [{ id: "A", label: "" }, { id: "B", label: "" }];
}

function initialCorrectAnswers(question?: AdminQuestionDetail) {
  const value = parseJson(question?.gradingConfigJson ?? "{}").correctAnswers;
  return Array.isArray(value) ? value.map(String) : [];
}

function nextOptionId(options: Option[]) {
  const used = new Set(options.map((option) => option.id));
  for (let index = 0; index < 26; index += 1) {
    const candidate = String.fromCharCode(65 + index);
    if (!used.has(candidate)) return candidate;
  }
  return `OPTION_${options.length + 1}`;
}

export function AdminQuestionEditor({ question }: AdminQuestionEditorProps) {
  const router = useRouter();
  const [form, setForm] = React.useState<AdminQuestionDetail>(question ?? {
    questionId: "", title: "", difficulty: 2, algorithmTag: "", knowledgeTags: "",
    estimatedMinutes: 20, trainingEnabled: 0, questionType: "PROGRAMMING",
    answerConfigJson: "{}", gradingConfigJson: "{}", timeLimit: 1000, spaceLimit: 262144,
    content: "", questionCase: "[]", defaultCode: "", mainFuc: ""
  });
  const initialAnswerConfig = React.useMemo(() => parseJson(question?.answerConfigJson ?? "{}"), [question]);
  const initialGradingConfig = React.useMemo(() => parseJson(question?.gradingConfigJson ?? "{}"), [question]);
  const [options, setOptions] = React.useState<Option[]>(() => initialOptions(question));
  const [correctAnswers, setCorrectAnswers] = React.useState<string[]>(() => initialCorrectAnswers(question));
  const [caseSensitive, setCaseSensitive] = React.useState(Boolean(initialGradingConfig.caseSensitive));
  const [rubric, setRubric] = React.useState(String(initialGradingConfig.rubric ?? ""));
  const [acceptedFormats, setAcceptedFormats] = React.useState(() => {
    const formats = initialAnswerConfig.acceptedFormats;
    return Array.isArray(formats) ? formats.join(",") : ".pdf,.zip,.txt";
  });
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  function updateField<K extends keyof AdminQuestionDetail>(key: K, value: AdminQuestionDetail[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function setQuestionType(questionType: string) {
    updateField("questionType", questionType);
    setCorrectAnswers(questionType === "TRUE_FALSE" ? ["true"] : []);
  }

  function toggleCorrect(id: string) {
    setCorrectAnswers((current) => form.questionType === "SINGLE_CHOICE"
      ? [id]
      : current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
  }

  function configs() {
    if (["SINGLE_CHOICE", "MULTIPLE_CHOICE"].includes(form.questionType)) return [{ options }, { correctAnswers, caseSensitive: true }];
    if (form.questionType === "TRUE_FALSE") return [{}, { correctAnswers, caseSensitive: true }];
    if (form.questionType === "FILL_BLANK") return [{ blankCount: Math.max(1, correctAnswers.length) }, { correctAnswers, caseSensitive }];
    if (form.questionType === "FILE") return [{ acceptedFormats: acceptedFormats.split(",").map((value) => value.trim()).filter(Boolean), maxSizeKb: 200 }, { rubric }];
    if (form.questionType === "PROJECT") return [{ requireRepositoryUrl: true }, { rubric }];
    if (["SHORT_ANSWER", "SQL"].includes(form.questionType)) return [{}, { rubric }];
    return [{ language: "java" }, { mode: "STANDARD" }];
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (frontendPreviewMode) return setError("当前是前端预览模式，题目改动不会提交到后端。");
    const [answerConfig, gradingConfig] = configs();
    setSubmitting(true); setError(null);
    try {
      const response = await fetch(adminApiPath("/questions"), {
        method: question ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form, answerConfigJson: JSON.stringify(answerConfig), gradingConfigJson: JSON.stringify(gradingConfig),
          difficulty: Number(form.difficulty), estimatedMinutes: Number(form.estimatedMinutes),
          trainingEnabled: Number(form.trainingEnabled), timeLimit: Number(form.timeLimit), spaceLimit: Number(form.spaceLimit)
        })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) throw new Error(payload?.message ?? "题目保存失败，请检查题型配置和必填项。");
      router.push(adminInternalPath("/questions")); router.refresh();
    } catch (err) { setError(err instanceof Error ? err.message : "题目保存失败。"); }
    finally { setSubmitting(false); }
  }

  async function handleDelete() {
    if (!question?.questionId || !window.confirm("确认删除这道题目吗？")) return;
    if (frontendPreviewMode) return setError("当前是前端预览模式，删除操作已禁用。");
    setSubmitting(true); setError(null);
    try {
      const response = await fetch(`${adminApiPath("/questions")}?questionId=${encodeURIComponent(question.questionId)}`, { method: "DELETE" });
      if (!response.ok) throw new Error("题目删除失败。");
      router.push(adminInternalPath("/questions")); router.refresh();
    } catch (err) { setError(err instanceof Error ? err.message : "题目删除失败。"); }
    finally { setSubmitting(false); }
  }

  const isChoice = ["SINGLE_CHOICE", "MULTIPLE_CHOICE"].includes(form.questionType);
  const needsRubric = ["SHORT_ANSWER", "SQL", "FILE", "PROJECT"].includes(form.questionType);

  return <Panel className="p-6"><form className="space-y-6" onSubmit={handleSubmit}>
    <div className="grid gap-4 md:grid-cols-2">
      <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">标题</span><Input required value={form.title} onChange={(event) => updateField("title", event.target.value)} /></label>
      <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">题型</span><select className={selectClassName} value={form.questionType} onChange={(event) => setQuestionType(event.target.value)}>{questionTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">难度</span><select className={selectClassName} value={form.difficulty} onChange={(event) => updateField("difficulty", Number(event.target.value))}><option value="1">Easy</option><option value="2">Medium</option><option value="3">Hard</option></select></label>
      <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">预计用时（分钟）</span><Input type="number" min="1" value={form.estimatedMinutes} onChange={(event) => updateField("estimatedMinutes", Number(event.target.value))} /></label>
      <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">分类标签</span><Input value={form.algorithmTag} onChange={(event) => updateField("algorithmTag", event.target.value)} /></label>
      <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">知识标签</span><Input value={form.knowledgeTags} onChange={(event) => updateField("knowledgeTags", event.target.value)} /></label>
    </div>
    <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">题面内容</span><Textarea required className="min-h-40" value={form.content} onChange={(event) => updateField("content", event.target.value)} /></label>

    {isChoice ? <section className="space-y-3 border-t border-[var(--border-soft)] pt-5">
      <div className="flex items-center justify-between"><div><h3 className="font-semibold">选项与正确答案</h3><p className="mt-1 text-xs text-[var(--text-muted)]">勾选正确项；多选题可以勾选多个。</p></div><Button type="button" size="sm" variant="secondary" onClick={() => setOptions((items) => [...items, { id: nextOptionId(items), label: "" }])}><Plus size={14} />添加选项</Button></div>
      {options.map((option, index) => <div key={`${option.id}-${index}`} className="grid grid-cols-[36px_1fr_36px] items-center gap-2">
        <input aria-label={`正确答案 ${option.id}`} type={form.questionType === "SINGLE_CHOICE" ? "radio" : "checkbox"} name="correct-answer" checked={correctAnswers.includes(option.id)} onChange={() => toggleCorrect(option.id)} />
        <Input value={option.label} placeholder={`选项 ${option.id}`} onChange={(event) => setOptions((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item))} />
        <Button aria-label="删除选项" type="button" size="sm" variant="ghost" disabled={options.length <= 2} onClick={() => { setOptions((items) => items.filter((_, itemIndex) => itemIndex !== index)); setCorrectAnswers((items) => items.filter((id) => id !== option.id)); }}><Trash2 size={15} /></Button>
      </div>)}
    </section> : null}
    {form.questionType === "TRUE_FALSE" ? <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">正确答案</span><select className={selectClassName} value={correctAnswers[0] ?? "true"} onChange={(event) => setCorrectAnswers([event.target.value])}><option value="true">正确</option><option value="false">错误</option></select></label> : null}
    {form.questionType === "FILL_BLANK" ? <div className="grid gap-4 md:grid-cols-[1fr_220px]"><label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">标准答案（每行一个空）</span><Textarea value={correctAnswers.join("\n")} onChange={(event) => setCorrectAnswers(event.target.value.split("\n").map((value) => value.trim()).filter(Boolean))} /></label><label className="flex items-center gap-3 self-end py-3 text-sm"><input type="checkbox" checked={caseSensitive} onChange={(event) => setCaseSensitive(event.target.checked)} />区分大小写</label></div> : null}
    {needsRubric ? <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">评分标准</span><Textarea required value={rubric} onChange={(event) => setRubric(event.target.value)} placeholder="列出得分点、扣分条件和可接受的答案范围" /></label> : null}
    {form.questionType === "FILE" ? <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">允许的文件扩展名</span><Input value={acceptedFormats} onChange={(event) => setAcceptedFormats(event.target.value)} placeholder=".pdf,.zip,.txt" /></label> : null}
    {form.questionType === "PROGRAMMING" ? <section className="space-y-4 border-t border-[var(--border-soft)] pt-5">
      <div className="grid gap-4 md:grid-cols-2"><label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">时间限制（ms）</span><Input type="number" min="1" value={form.timeLimit} onChange={(event) => updateField("timeLimit", Number(event.target.value))} /></label><label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">空间限制（KB）</span><Input type="number" min="1" value={form.spaceLimit} onChange={(event) => updateField("spaceLimit", Number(event.target.value))} /></label></div>
      <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">判题用例 JSON</span><Textarea value={form.questionCase} onChange={(event) => updateField("questionCase", event.target.value)} /></label>
      <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">默认代码</span><Textarea value={form.defaultCode} onChange={(event) => updateField("defaultCode", event.target.value)} /></label>
      <label className="space-y-2"><span className="text-sm text-[var(--text-secondary)]">主函数片段</span><Textarea value={form.mainFuc} onChange={(event) => updateField("mainFuc", event.target.value)} /></label>
    </section> : null}
    {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
    <div className="flex flex-wrap gap-3"><Button type="submit" disabled={submitting}>{submitting ? <LoaderCircle size={14} className="animate-spin" /> : null}{frontendPreviewMode ? "预览模式下不可保存" : "保存题目"}</Button>{question ? <Button type="button" variant="secondary" disabled={submitting} onClick={() => void handleDelete()}>{frontendPreviewMode ? "预览模式下不可删除" : "删除题目"}</Button> : null}</div>
  </form></Panel>;
}
