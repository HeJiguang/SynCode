"use client";

import * as React from "react";
import { ArrowRight, CheckCircle2, Mail, ShieldCheck, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

import { setBrowserAccessToken } from "@aioj/api";
import { Button, Input, Panel, Tag } from "@aioj/ui";
import { appApiPath, appInternalPath } from "../../lib/paths";

function AuthSignal({
  label,
  title,
  description,
  icon
}: {
  label: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-[22px] border border-white/10 bg-white/[0.03] p-5 backdrop-blur-md transition-all duration-300 ease-out hover:border-white/20 hover:bg-white/[0.05]">
      <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-zinc-100">
        {icon}
      </div>
      <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">{label}</p>
      <h3 className="mt-2 text-base font-semibold text-zinc-50">{title}</h3>
      <p className="mt-2 text-sm leading-7 text-zinc-400">{description}</p>
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [code, setCode] = React.useState("");
  const [status, setStatus] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

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

  const statusTone = status?.includes("失败") ? "text-rose-300" : "text-emerald-300";

  return (
    <main className="min-h-screen bg-[var(--bg)] px-4 py-6 md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-[1400px] gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <Panel className="hero-grid hidden overflow-hidden p-8 lg:flex lg:flex-col lg:justify-between" tone="accent">
          <div className="relative space-y-8">
            <div>
              <p className="kicker">SynCode Access</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Tag tone="accent">Voyager Console</Tag>
                <Tag>Developer Workflow</Tag>
                <Tag>Secure Sign-in</Tag>
              </div>
            </div>

            <div className="max-w-3xl">
              <h1 className="text-5xl font-semibold leading-[1.02] tracking-[-0.06em] text-zinc-50">
                登录后继续你的
                <br />
                训练、考试与 AI 工作流
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-[var(--text-secondary)]">
                SynCode 会把当前训练计划、考试工作区、提交记录和 AI 上下文收束到同一个控制台里。你登录后看到的不是零散页面，而是一条连续的工作主线。
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <AuthSignal
                label="Training"
                title="持续训练主线"
                description="把当前方向、任务进度和待补强项稳定地放在同一张面板里。"
                icon={<Sparkles size={18} />}
              />
              <AuthSignal
                label="Exam"
                title="进入考试工作区"
                description="考试状态、题面、编辑器和判题反馈保持在同一个上下文中。"
                icon={<ShieldCheck size={18} />}
              />
              <AuthSignal
                label="Access"
                title="邮箱验证码登录"
                description="用一次性验证码完成登录，不需要额外维护复杂密码体系。"
                icon={<Mail size={18} />}
              />
            </div>
          </div>

          <div className="flex items-center justify-between rounded-[22px] border border-white/10 bg-white/[0.03] px-5 py-4 backdrop-blur-md">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--text-faint)]">Next Step</p>
              <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">获取验证码并进入控制台，继续你上一次中断的训练上下文。</p>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-zinc-100">
              <ArrowRight size={16} />
            </div>
          </div>
        </Panel>

        <Panel className="flex items-center justify-center p-6 md:p-10" tone="strong">
          <div className="w-full max-w-[440px]">
            <p className="kicker">Access</p>
            <h2 className="mt-3 text-3xl font-semibold text-zinc-50">登录 SynCode</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
              输入邮箱，先获取验证码，再进入工作台。登录成功后会恢复你的个人训练数据和历史提交上下文。
            </p>

            <div className="mt-6 rounded-[22px] border border-white/10 bg-white/[0.03] p-5 backdrop-blur-md">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--text-faint)]" htmlFor="email">
                    Email
                  </label>
                  <Input
                    id="email"
                    autoComplete="email"
                    placeholder="输入邮箱地址"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--text-faint)]" htmlFor="code">
                    Verification Code
                  </label>
                  <div className="grid gap-3 md:grid-cols-[1fr_132px]">
                    <Input
                      id="code"
                      inputMode="numeric"
                      placeholder="输入验证码"
                      value={code}
                      onChange={(event) => setCode(event.target.value)}
                    />
                    <Button disabled={loading || !email} variant="secondary" onClick={sendCode}>
                      发送验证码
                    </Button>
                  </div>
                </div>

                <Button className="w-full" disabled={loading || !email || !code} size="lg" onClick={login}>
                  登录并进入工作台
                </Button>

                {status ? (
                  <div className="flex items-start gap-3 rounded-[18px] border border-white/10 bg-white/[0.03] px-4 py-3">
                    <CheckCircle2 size={16} className={`mt-0.5 shrink-0 ${statusTone}`} />
                    <p className={`text-sm leading-7 ${statusTone}`}>{status}</p>
                  </div>
                ) : null}
              </div>
            </div>

            <p className="mt-4 text-xs leading-6 text-[var(--text-muted)]">
              验证码会发送到你的邮箱。若暂未收到，请先确认邮箱地址可用，再重新发送。
            </p>
          </div>
        </Panel>
      </div>
    </main>
  );
}
