import * as React from "react";
import { ArrowRight, ArrowUpRight, Bot, BrainCircuit, PanelsTopLeft, Sparkles } from "lucide-react";

import { githubUrl } from "@aioj/config";
import { Button, Panel, Tag } from "@aioj/ui";

const heroStats = [
  { value: "1", label: "统一工作流" },
  { value: "3x", label: "更快定位问题" },
  { value: "24/7", label: "随时进入训练" }
];

const timelineItems = [
  { title: "系统提示", body: "题面、训练目标和上下文会先收束到一个稳定工作区。", tone: "dim" },
  { title: "用户操作", body: "在编辑器、训练面板和考试工作区之间保持同一条链路。", tone: "neutral" },
  { title: "AI 响应", body: "建议、定位与反馈只在关键节点出现，不制造视觉噪音。", tone: "accent" }
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
      <section className="px-4 py-4 md:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between rounded-[22px] border border-[var(--border-soft)] bg-[var(--surface-overlay)] px-4 py-3 backdrop-blur-xl">
          <a className="flex items-center gap-3 transition-opacity hover:opacity-85" href="/">
            <div className="flex h-9 w-9 items-center justify-center rounded-[12px] bg-white text-[12px] font-bold tracking-[0.12em] text-[#09111a]">
              SC
            </div>
            <div>
              <p className="text-sm font-semibold text-[var(--text-primary)]">SynCode</p>
              <p className="text-[11px] text-[var(--text-faint)]">AI 辅助编程训练平台</p>
            </div>
          </a>

          <div className="flex items-center gap-2">
            <a href="/app">
              <Button size="sm">开始体验</Button>
            </a>
            <a href={githubUrl} rel="noreferrer" target="_blank">
              <Button size="sm" variant="secondary">
                GitHub
              </Button>
            </a>
          </div>
        </div>
      </section>

      <section className="px-4 pb-10 pt-10 md:px-8 md:pt-16">
        <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="flex flex-col justify-between gap-8">
            <div className="space-y-6">
              <Tag tone="accent" className="px-3 py-1 text-[10px]">
                AI-native workflow
              </Tag>
              <div className="space-y-5">
                <h1 className="max-w-[560px] text-[clamp(3rem,5vw,5.5rem)] font-semibold leading-[0.96] tracking-[-0.07em] text-white">
                  让 AI 成为你的
                  <br />
                  编程训练搭档
                </h1>
                <p className="max-w-[560px] text-[17px] leading-8 text-[var(--text-secondary)]">
                  SynCode 把题库、训练、考试、代码编辑与 AI 辅助串成一条稳定的练习链路。你不需要在多个页面之间来回切换，重点始终留在当前问题本身。
                </p>
              </div>
              <div className="flex flex-wrap gap-3 pt-2">
                <a href="/app">
                  <Button className="h-12 px-7 text-[15px]" size="lg">
                    进入系统
                  </Button>
                </a>
                <a href={githubUrl} rel="noreferrer" target="_blank">
                  <Button className="h-12 px-7 text-[15px]" size="lg" variant="secondary">
                    GitHub
                    <ArrowUpRight size={16} />
                  </Button>
                </a>
              </div>
            </div>

            <div className="grid gap-6 border-t border-[var(--border-soft)] pt-8 sm:grid-cols-3">
              {heroStats.map((item) => (
                <div key={item.label}>
                  <p className="font-mono text-4xl font-semibold tracking-[-0.04em] text-white">{item.value}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.14em] text-[var(--text-faint)]">{item.label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <Panel className="p-6 xl:col-span-2" tone="accent">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="kicker">Problem Setup</p>
                  <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-white">两数之和</h2>
                  <p className="mt-2 text-sm text-[var(--text-secondary)]">数组 / 哈希表 / 预计 15 分钟</p>
                </div>
                <Tag tone="success">Easy</Tag>
              </div>
              <div className="mt-6 rounded-[20px] border border-[var(--border-soft)] bg-black/20 p-4 text-sm leading-7 text-[var(--text-secondary)]">
                题面、代码编辑器、运行结果和 AI 分析会停留在同一视图里，减少上下文切换。训练系统只在真正需要时给出建议，而不是持续打断你。
              </div>
            </Panel>

            <Panel className="p-5" hoverable>
              <p className="kicker">Editor Focus</p>
              <div className="mt-4 rounded-[20px] border border-[var(--border-soft)] bg-[#0b0d15] p-5 font-mono text-[13px] leading-7 text-[#d9e6ff]">
                <p className="text-[#64708f]">// Find complement</p>
                <p>Map&lt;Integer, Integer&gt; seen = new HashMap&lt;&gt;();</p>
                <p className="mt-2">for (int i = 0; i &lt; nums.length; i++) {"{"}</p>
                <p className="pl-4">int rem = target - nums[i];</p>
                <p className="pl-4 text-[#45d8a3]">if (seen.containsKey(rem)) return ...;</p>
                <p>{"}"}</p>
              </div>
            </Panel>

            <Panel className="p-5" hoverable>
              <p className="kicker">Training Pulse</p>
              <h3 className="mt-3 text-lg font-semibold text-white">系统联动提示</h3>
              <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
                热题、公告、训练目标和最近提交会在一个控制台里自然汇合，而不是散落在多个孤立页面里。
              </p>
              <div className="mt-5 rounded-[18px] border border-[rgba(130,233,194,0.24)] bg-[rgba(70,216,162,0.08)] p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">AI Suggestion</p>
                <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">
                  当前题目更适合先查后存的写法，这样能避免索引覆盖带来的边界错误。
                </p>
              </div>
            </Panel>
          </div>
        </div>
      </section>

      <section className="px-4 pb-20 pt-8 md:px-8">
        <div className="mx-auto grid max-w-7xl gap-6 xl:grid-cols-[0.92fr_1.08fr]">
          <Panel className="p-7 md:p-8">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-[16px] border border-[var(--border-soft)] bg-white/[0.04] text-white">
                <Sparkles size={18} />
              </div>
              <div>
                <p className="kicker text-[var(--accent)]">Workflow Console</p>
                <h2 className="mt-1 text-[32px] font-semibold leading-none tracking-[-0.05em] text-white">一条更稳的学习主线</h2>
              </div>
            </div>

            <div className="mt-8 space-y-4 text-[15px] leading-8 text-[var(--text-secondary)]">
              <p>不是把很多卡片堆在一起，而是把你下一步真正要做的动作放到最前面。</p>
              <p>从进入题目，到执行代码、查看结果，再到训练反馈，SynCode 保持同一个上下文和同一套视觉语言。</p>
            </div>

            <div className="mt-8 space-y-4">
              {[
                { icon: <BrainCircuit size={16} />, text: "Prompt 与题目上下文自动收束，不需要重复描述背景。" },
                { icon: <PanelsTopLeft size={16} />, text: "题库、训练、考试和个人进度都用统一的控制台语义组织。" },
                { icon: <Bot size={16} />, text: "AI 只在关键节点出现，避免廉价感很重的全屏装饰和泛滥提示。" }
              ].map((item) => (
                <div key={item.text} className="flex items-start gap-3 rounded-[18px] border border-[var(--border-soft)] bg-white/[0.02] px-4 py-4">
                  <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-[12px] bg-white/[0.04] text-[var(--accent)]">
                    {item.icon}
                  </div>
                  <p className="text-sm leading-7 text-[var(--text-secondary)]">{item.text}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel className="overflow-hidden p-0" tone="accent">
            <div className="grid gap-0 xl:grid-cols-[1.1fr_0.9fr]">
              <div className="border-b border-[var(--border-soft)] p-7 xl:border-b-0 xl:border-r">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="kicker">Session Preview</p>
                    <h3 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">工作流预览</h3>
                  </div>
                  <Tag tone="accent">Live</Tag>
                </div>

                <div className="mt-6 rounded-[22px] border border-[var(--border-soft)] bg-[#111427] p-5">
                  <div className="mb-5 flex items-center gap-2">
                    <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
                    <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
                    <span className="h-3 w-3 rounded-full bg-[#28c840]" />
                  </div>
                  <div className="space-y-4">
                    <div className="rounded-[18px] bg-[#171b31] p-4">
                      <p className="text-sm text-[#dce5ff]">请解释 E = mc² 的含义，并给出编程竞赛中常见的推导误区。</p>
                    </div>
                    <div className="rounded-[18px] bg-[#0d1021] p-4 text-sm leading-7 text-[#9aa5c7]">
                      这里保留一个清晰的对话区，但不会让整个页面退化成聊天模板。训练信息、题目状态和操作入口仍然是主角。
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-7">
                <p className="kicker">Timeline</p>
                <div className="mt-5 space-y-5">
                  {timelineItems.map((item) => (
                    <div key={item.title} className="relative rounded-[18px] border border-[var(--border-soft)] bg-white/[0.03] px-4 py-4">
                      <span
                        className={`absolute left-0 top-4 h-8 w-[3px] rounded-r-full ${
                          item.tone === "accent" ? "bg-[var(--accent)]" : item.tone === "neutral" ? "bg-[#7d8bb4]" : "bg-white/12"
                        }`}
                      />
                      <p className="pl-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--text-faint)]">{item.title}</p>
                      <p className="mt-2 pl-3 text-sm leading-7 text-[var(--text-secondary)]">{item.body}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-8">
                  <a href="/app">
                    <Button className="h-12 w-full text-[15px]" size="lg">
                      进入 SynCode
                      <ArrowRight size={16} />
                    </Button>
                  </a>
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </section>
    </main>
  );
}
