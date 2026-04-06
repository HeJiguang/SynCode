"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { frontendPreviewMode } from "@aioj/config";
import { Button, Panel } from "@aioj/ui";
import { adminApiPath } from "../lib/paths";

type AdminNoticeActionsProps = {
  noticeId: string;
  status: number;
  isPinned: number;
};

export function AdminNoticeActions({ noticeId, status, isPinned }: AdminNoticeActionsProps) {
  const router = useRouter();
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function invoke(endpoint: string, payload: Record<string, unknown>) {
    if (frontendPreviewMode) {
      setError("当前是前端预览模式，公告状态操作不会提交到后端。");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(endpoint, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const body = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) {
        throw new Error(body?.message ?? "公告操作失败。");
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "公告操作失败。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Panel className="p-5">
      <p className="kicker">Actions</p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Button type="button" disabled={loading} onClick={() => invoke(adminApiPath("/notices/publish"), { noticeId, publish: status !== 1 })}>
          {frontendPreviewMode ? "预览模式下不可发布" : status === 1 ? "撤回发布" : "发布公告"}
        </Button>
        <Button type="button" variant="secondary" disabled={loading} onClick={() => invoke(adminApiPath("/notices/pin"), { noticeId, pinned: isPinned !== 1 })}>
          {frontendPreviewMode ? "预览模式下不可置顶" : isPinned === 1 ? "取消置顶" : "设为置顶"}
        </Button>
      </div>
      {error ? <p className="mt-3 text-sm text-[var(--danger)]">{error}</p> : null}
    </Panel>
  );
}
