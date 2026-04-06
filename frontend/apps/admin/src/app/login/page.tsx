"use client";

import * as React from "react";
import { frontendPreviewMode } from "@aioj/config";
import { Button, Input, Panel, Tag } from "@aioj/ui";

import { adminApiPath, adminPublicPath } from "../../lib/paths";

export default function AdminLoginPage() {
  const [userAccount, setUserAccount] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(adminApiPath("/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userAccount, password })
      });

      const payload = (await response.json().catch(() => ({}))) as { message?: string };
      if (!response.ok) {
        throw new Error(payload.message ?? "管理员登录失败。");
      }

      window.location.href = adminPublicPath("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "管理员登录失败。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="grid w-full max-w-5xl gap-6 lg:grid-cols-[1fr_420px]">
        <Panel className="p-8">
          <Tag tone="accent">Admin</Tag>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight">SynCode 管理端入口</h1>
          <p className="mt-4 text-base leading-8 text-[var(--text-secondary)]">
            管理端不再从官网或用户端暴露入口。只有具备管理员权限的账号，才应该从独立的 `/admin` 路径进入系统。
          </p>
        </Panel>
        <Panel className="p-8">
          <h2 className="text-2xl font-semibold">管理员登录</h2>
          {frontendPreviewMode ? (
            <div className="mt-4 rounded-[18px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3 text-sm leading-7 text-[var(--text-secondary)]">
              当前本地已开启前端预览模式。你可以跳过管理员登录，直接进入后台界面预览和改样式。
            </div>
          ) : null}
          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <Input placeholder="请输入管理员账号" value={userAccount} onChange={(event) => setUserAccount(event.target.value)} />
            <Input placeholder="请输入密码" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
            <Button className="w-full" size="lg" type="submit" disabled={submitting}>
              {submitting ? "登录中..." : "登录后台"}
            </Button>
            {frontendPreviewMode ? (
              <a href={adminPublicPath("/")} className="block">
                <Button className="w-full" size="lg" type="button" variant="secondary">
                  直接进入预览后台
                </Button>
              </a>
            ) : null}
          </form>
        </Panel>
      </div>
    </main>
  );
}
