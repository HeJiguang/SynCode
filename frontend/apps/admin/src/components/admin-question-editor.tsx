"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle } from "lucide-react";

import type { AdminQuestionDetail } from "../lib/admin-api";
import { adminApiPath, adminInternalPath } from "../lib/paths";
import { Button, Input, Panel, Textarea } from "@aioj/ui";

type AdminQuestionEditorProps = {
  question?: AdminQuestionDetail;
};

const selectClassName =
  "h-11 rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--border-strong)]";

export function AdminQuestionEditor({ question }: AdminQuestionEditorProps) {
  const router = useRouter();
  const [form, setForm] = React.useState<AdminQuestionDetail>(
    question ?? {
      questionId: "",
      title: "",
      difficulty: 2,
      algorithmTag: "",
      knowledgeTags: "",
      estimatedMinutes: 20,
      trainingEnabled: 0,
      timeLimit: 1000,
      spaceLimit: 262144,
      content: "",
      questionCase: "[]",
      defaultCode: "",
      mainFuc: ""
    }
  );
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  function updateField<K extends keyof AdminQuestionDetail>(key: K, value: AdminQuestionDetail[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(adminApiPath("/questions"), {
        method: question ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          difficulty: Number(form.difficulty),
          estimatedMinutes: Number(form.estimatedMinutes),
          trainingEnabled: Number(form.trainingEnabled),
          timeLimit: Number(form.timeLimit),
          spaceLimit: Number(form.spaceLimit)
        })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "题目保存失败。");
      }
      router.push(adminInternalPath("/questions"));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "题目保存失败。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!question?.questionId || !window.confirm("确认删除这道题目吗？")) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${adminApiPath("/questions")}?questionId=${encodeURIComponent(question.questionId)}`, {
        method: "DELETE"
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "题目删除失败。");
      }
      router.push(adminInternalPath("/questions"));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "题目删除失败。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Panel className="p-6">
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">标题</span>
            <Input value={form.title} onChange={(event) => updateField("title", event.target.value)} />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">难度</span>
            <select className={selectClassName} value={String(form.difficulty)} onChange={(event) => updateField("difficulty", Number(event.target.value))}>
              <option value="1">Easy</option>
              <option value="2">Medium</option>
              <option value="3">Hard</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">算法标签</span>
            <Input value={form.algorithmTag} onChange={(event) => updateField("algorithmTag", event.target.value)} />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">知识标签</span>
            <Input value={form.knowledgeTags} onChange={(event) => updateField("knowledgeTags", event.target.value)} />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">预计用时（分钟）</span>
            <Input type="number" value={String(form.estimatedMinutes)} onChange={(event) => updateField("estimatedMinutes", Number(event.target.value))} />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">训练推荐</span>
            <select className={selectClassName} value={String(form.trainingEnabled)} onChange={(event) => updateField("trainingEnabled", Number(event.target.value))}>
              <option value="0">关闭</option>
              <option value="1">开启</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">时间限制（ms）</span>
            <Input type="number" value={String(form.timeLimit)} onChange={(event) => updateField("timeLimit", Number(event.target.value))} />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">空间限制（KB）</span>
            <Input type="number" value={String(form.spaceLimit)} onChange={(event) => updateField("spaceLimit", Number(event.target.value))} />
          </label>
        </div>

        <label className="space-y-2">
          <span className="text-sm text-[var(--text-secondary)]">题面内容</span>
          <Textarea value={form.content} onChange={(event) => updateField("content", event.target.value)} />
        </label>
        <label className="space-y-2">
          <span className="text-sm text-[var(--text-secondary)]">样例与判题用例 JSON</span>
          <Textarea value={form.questionCase} onChange={(event) => updateField("questionCase", event.target.value)} />
        </label>
        <label className="space-y-2">
          <span className="text-sm text-[var(--text-secondary)]">默认代码</span>
          <Textarea value={form.defaultCode} onChange={(event) => updateField("defaultCode", event.target.value)} />
        </label>
        <label className="space-y-2">
          <span className="text-sm text-[var(--text-secondary)]">主函数片段</span>
          <Textarea value={form.mainFuc} onChange={(event) => updateField("mainFuc", event.target.value)} />
        </label>

        {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={submitting}>
            {submitting ? <LoaderCircle size={14} className="animate-spin" /> : null}
            保存题目
          </Button>
          {question ? (
            <Button type="button" variant="secondary" disabled={submitting} onClick={handleDelete}>
              删除题目
            </Button>
          ) : null}
        </div>
      </form>
    </Panel>
  );
}
