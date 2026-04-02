"use client";

import * as React from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { setBrowserAccessToken } from "@aioj/api";
import { Button, Input, Panel, Tag } from "@aioj/ui";
import { appApiPath, appInternalPath } from "../../lib/paths";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function sendCode() {
    setLoading(true);
    setStatus(null);

    try {
      const response = await fetch(appApiPath("/auth/send-code"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "发送验证码失败。");
      }

      setStatus("验证码已发送，请检查邮箱。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "发送验证码失败。");
    } finally {
      setLoading(false);
    }
  }

  async function login() {
    setLoading(true);
    setStatus(null);

    try {
      const response = await fetch(appApiPath("/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code })
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "登录失败。");
      }

      setBrowserAccessToken(payload.token);
      router.push(appInternalPath("/"));
      router.refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "登录失败。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-[1400px] gap-4 lg:grid-cols-[1.12fr_0.88fr]">
        <Panel className="hero-grid hidden overflow-hidden p-8 lg:flex lg:flex-col lg:justify-between" tone="accent">
          <div className="relative">
            <p className="kicker">SynCode</p>
            <h1 className="mt-3 max-w-xl text-5xl font-semibold leading-tight tracking-[-0.05em]">
              登录后继续你的训练
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-[var(--text-secondary)]">
              使用邮箱验证码即可进入工作台，继续刷题、训练、考试和 AI 辅助编程流程。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Tag tone="accent">训练计划</Tag>
              <Tag>实时判题</Tag>
              <Tag>AI 辅助</Tag>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-black/10 px-4 py-4">
              <p className="text-xs text-[var(--text-muted)]">题目工作区</p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-primary)]">题面、代码、判题和 AI 建议集中在同一视图中。</p>
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-black/10 px-4 py-4">
              <p className="text-xs text-[var(--text-muted)]">训练路径</p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-primary)]">按当前阶段生成目标、任务和补强方向。</p>
            </div>
            <div className="rounded-[20px] border border-[var(--border-soft)] bg-black/10 px-4 py-4">
              <p className="text-xs text-[var(--text-muted)]">学习记录</p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-primary)]">提交趋势、热力图和个人资料会自动同步更新。</p>
            </div>
          </div>
        </Panel>

        <Panel className="flex items-center justify-center p-6 md:p-10" tone="strong">
          <div className="w-full max-w-[460px]">
            <p className="kicker">登录入口</p>
            <h2 className="mt-3 text-3xl font-semibold">登录 SynCode</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
              输入邮箱后先获取验证码，再完成登录。
            </p>

            <div className="mt-6 space-y-4">
              <Input placeholder="输入邮箱地址" value={email} onChange={(event) => setEmail(event.target.value)} />

              <div className="grid gap-3 md:grid-cols-[1fr_120px]">
                <Input placeholder="输入验证码" value={code} onChange={(event) => setCode(event.target.value)} />
                <Button disabled={loading || !email} variant="secondary" onClick={sendCode}>
                  发送验证码
                </Button>
              </div>

              <Button className="w-full" disabled={loading || !email || !code} size="lg" onClick={login}>
                登录
              </Button>

              {status ? <p className="text-sm text-[var(--text-secondary)]">{status}</p> : null}
            </div>
          </div>
        </Panel>
      </div>
    </main>
  );
}
