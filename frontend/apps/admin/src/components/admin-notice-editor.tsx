"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle } from "lucide-react";

import { frontendPreviewMode } from "@aioj/config";
import type { AdminNoticeDetail } from "../lib/admin-api";
import { adminApiPath, adminInternalPath } from "../lib/paths";
import { Button, Input, Panel, Textarea } from "@aioj/ui";

type AdminNoticeEditorProps = {
  notice?: AdminNoticeDetail;
};

const fieldClassName =
  "h-11 rounded-[14px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--border-strong)]";

export function AdminNoticeEditor({ notice }: AdminNoticeEditorProps) {
  const router = useRouter();
  const [form, setForm] = React.useState({
    noticeId: notice?.noticeId,
    title: notice?.title ?? "",
    category: notice?.category ?? "公告",
    isPublic: notice?.isPublic ?? 1,
    isPinned: notice?.isPinned ?? 0,
    content: notice?.content ?? ""
  });
  const [submitting, setSubmitting] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    setError(null);

    if (frontendPreviewMode) {
      setSubmitting(false);
      setMessage("当前是前端预览模式，公告改动不会提交到后端。");
      return;
    }

    try {
      const response = await fetch(adminApiPath("/notices"), {
        method: notice ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });

      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "公告保存失败。");
      }

      setMessage("公告已保存。");
      router.push(adminInternalPath("/notices"));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "公告保存失败。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!notice?.noticeId || !window.confirm("确认删除这条公告吗？")) return;
    if (frontendPreviewMode) {
      setError("当前是前端预览模式，删除操作已禁用。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${adminApiPath("/notices")}?noticeId=${encodeURIComponent(notice.noticeId)}`, {
        method: "DELETE"
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(payload?.message ?? "公告删除失败。");
      }
      router.push(adminInternalPath("/notices"));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "公告删除失败。");
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
            <Input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">分类</span>
            <Input value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} />
          </label>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">公开范围</span>
            <select
              className={fieldClassName}
              value={String(form.isPublic)}
              onChange={(event) => setForm((current) => ({ ...current, isPublic: Number(event.target.value) }))}
            >
              <option value="1">公开</option>
              <option value="0">仅内部</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm text-[var(--text-secondary)]">置顶状态</span>
            <select
              className={fieldClassName}
              value={String(form.isPinned)}
              onChange={(event) => setForm((current) => ({ ...current, isPinned: Number(event.target.value) }))}
            >
              <option value="0">普通</option>
              <option value="1">置顶</option>
            </select>
          </label>
        </div>

        <label className="space-y-2">
          <span className="text-sm text-[var(--text-secondary)]">正文</span>
          <Textarea value={form.content} onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))} />
        </label>

        {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
        {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={submitting}>
            {submitting ? <LoaderCircle size={14} className="animate-spin" /> : null}
            {frontendPreviewMode ? "预览模式下不可保存" : "保存公告"}
          </Button>
          {notice ? (
            <Button type="button" variant="secondary" disabled={submitting} onClick={handleDelete}>
              {frontendPreviewMode ? "预览模式下不可删除" : "删除公告"}
            </Button>
          ) : null}
        </div>
      </form>
    </Panel>
  );
}
