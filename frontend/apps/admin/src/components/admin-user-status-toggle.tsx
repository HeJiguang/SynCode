"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { frontendPreviewMode } from "@aioj/config";
import { Button } from "@aioj/ui";
import { adminApiPath } from "../lib/paths";

type AdminUserStatusToggleProps = {
  userId: string;
  status: "正常" | "冻结";
};

export function AdminUserStatusToggle({ userId, status }: AdminUserStatusToggleProps) {
  const router = useRouter();
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const nextStatus = status === "正常" ? 1 : 0;

  async function handleClick() {
    if (frontendPreviewMode) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(adminApiPath("/users/status"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId, status: nextStatus })
      });
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      if (!response.ok) throw new Error(payload?.message ?? "用户状态更新失败。");
      router.refresh();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "用户状态更新失败。");
    } finally {
      setLoading(false);
    }
  }

  return <div className="flex flex-col items-end gap-1">
    <Button type="button" variant="ghost" size="sm" disabled={loading || frontendPreviewMode} onClick={handleClick}>
      {frontendPreviewMode ? "预览模式" : status === "正常" ? "冻结" : "恢复"}
    </Button>
    {error ? <span className="text-xs text-[var(--danger)]">{error}</span> : null}
  </div>;
}
