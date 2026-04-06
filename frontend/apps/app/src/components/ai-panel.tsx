"use client";

import * as React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { AiArtifact, AiRunCreateResponse, AiRunEvent, CodeLanguage } from "@aioj/api";
import { frontendPreviewMode } from "@aioj/config";
import { Check, Code2, Copy, Send, Sparkles, X } from "lucide-react";

import type { JudgeResultDetail } from "../lib/judge-result";
import { appApiPath } from "../lib/paths";
import { Button } from "@aioj/ui";


type AiPanelProps = {
  initialArtifacts?: AiArtifact[];
  questionId?: string;
  questionTitle?: string;
  questionContent?: string;
};

type Block = { type: "text"; content: string } | { type: "code"; lang: string; content: string };

type CodeContextDetail = {
  questionId?: string;
  questionTitle?: string;
  questionContent?: string;
  language: CodeLanguage;
  code: string;
};

type RunType =
  | "interactive_tutor"
  | "interactive_diagnosis"
  | "interactive_recommendation"
  | "interactive_review"
  | "interactive_plan";

type TimelineEntry =
  | { id: string; kind: "prompt"; content: string }
  | { id: string; kind: "artifact"; artifact: AiArtifact };

const QUICK_ACTIONS: Array<{ label: string; runType: RunType }> = [
  { label: "解题提示", runType: "interactive_tutor" },
  { label: "分析提交", runType: "interactive_diagnosis" },
  { label: "接下来练什么", runType: "interactive_recommendation" }
];

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const codeRe = /```(\w*)\n?([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeRe.exec(text)) !== null) {
    if (match.index > lastIndex) {
      blocks.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }
    blocks.push({ type: "code", lang: match[1] || "plain", content: match[2].trimEnd() });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    blocks.push({ type: "text", content: text.slice(lastIndex) });
  }

  return blocks;
}

function parseRunEvents(streamText: string): AiRunEvent[] {
  return streamText
    .replace(/\r/g, "")
    .split("\n\n")
    .map((chunk) =>
      chunk
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.replace(/^data:\s?/, ""))
        .join("\n")
        .trim()
    )
    .filter(Boolean)
    .map((chunk) => JSON.parse(chunk) as AiRunEvent);
}

function artifactText(artifact: AiArtifact, key: string) {
  const value = artifact.body[key];
  return typeof value === "string" ? value : "";
}

function formatEventLabel(event: AiRunEvent) {
  const node = typeof event.payload.node === "string" ? event.payload.node : null;
  if (event.eventType === "graph.node_completed" && node) {
    return `Node completed: ${node}`;
  }
  if (event.eventType === "artifact.created") {
    return `已生成结果卡片：${String(event.payload.artifactType ?? "unknown")}`;
  }
  return event.eventType.replace(/\./g, " ");
}

function buildErrorArtifact(message: string): AiArtifact {
  return {
    artifactId: `art-error-${Date.now()}`,
    runId: "local-error",
    artifactType: "answer_card",
    title: "Run failed",
    summary: "The workspace runtime could not complete this request.",
    body: {
      answer: message,
      nextAction: "检查当前代码和判题结果后重试，必要时先发起一次提示型问答。"
    },
    renderHint: "timeline_card",
    version: 1,
    createdAt: new Date().toISOString()
  };
}

function toTimelineEntries(artifacts: AiArtifact[]) {
  return artifacts.map(
    (artifact): TimelineEntry => ({
      id: artifact.artifactId,
      kind: "artifact",
      artifact
    })
  );
}

function mergeArtifacts(current: TimelineEntry[], artifacts: AiArtifact[]) {
  const knownIds = new Set(
    current.filter((item) => item.kind === "artifact").map((item) => item.artifact.artifactId)
  );
  const nextEntries = artifacts
    .filter((artifact) => !knownIds.has(artifact.artifactId))
    .map(
      (artifact): TimelineEntry => ({
        id: artifact.artifactId,
        kind: "artifact",
        artifact
      })
    );
  return [...current, ...nextEntries];
}

function CodeBlock({ lang, content }: { lang: string; content: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="my-3 overflow-hidden rounded-[var(--radius-sm)] border border-[var(--border-soft)]">
      <div className="flex items-center justify-between border-b border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">
        <span className="inline-flex items-center gap-1.5">
          <Code2 size={12} />
          {lang}
        </span>
        <button
          type="button"
          onClick={() => void copy()}
          className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-semibold text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-1)] hover:text-[var(--text-primary)]"
        >
          {copied ? <Check size={11} /> : <Copy size={11} />}
          {copied ? "已复制" : "复制"}
        </button>
      </div>
      <pre className="overflow-x-auto bg-[var(--surface-1)] px-4 py-3 text-[12px] leading-relaxed text-[var(--text-primary)]">
        <code>{content}</code>
      </pre>
    </div>
  );
}

function PromptBubble({ content }: { content: string }) {
  return (
    <div className="-mx-4 border-b border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">Query</p>
      <p className="mt-2 text-sm leading-6 text-[var(--text-primary)]">{content}</p>
    </div>
  );
}

function ArtifactCard({ artifact }: { artifact: AiArtifact }) {
  const answer = artifactText(artifact, "answer");
  const nextAction = artifactText(artifact, "nextAction");
  const intent = artifactText(artifact, "intent");
  const blocks = parseBlocks(answer);

  return (
    <div className="-mx-5 border-l-2 border-[var(--accent)] bg-[var(--surface-2)] px-5 py-4 pl-9">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">结果</p>
          <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{artifact.title}</p>
          {artifact.summary ? (
            <p className="mt-1 text-xs leading-5 text-[var(--text-secondary)]">{artifact.summary}</p>
          ) : null}
        </div>
        <div className="shrink-0 rounded-full border border-[var(--border-soft)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">
          {artifact.renderHint}
        </div>
      </div>

      {intent ? (
        <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">
          意图：{intent}
        </p>
      ) : null}

      {blocks.length > 0 ? (
        <div className="mt-3">
          {blocks.map((block, index) =>
            block.type === "code" ? (
              <CodeBlock key={`${artifact.artifactId}-code-${index}`} lang={block.lang} content={block.content} />
            ) : (
              <p key={`${artifact.artifactId}-text-${index}`} className="whitespace-pre-wrap text-sm leading-6 text-[var(--text-secondary)]">
                {block.content}
              </p>
            )
          )}
        </div>
      ) : null}

      {nextAction ? (
        <div className="mt-4 rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-1)] px-3 py-2">
          <p className="text-sm leading-6 text-[var(--text-primary)]">{nextAction}</p>
        </div>
      ) : null}
    </div>
  );
}

export function AiPanel({
  initialArtifacts = [],
  questionId,
  questionTitle,
  questionContent
}: AiPanelProps) {
  const [entries, setEntries] = useState<TimelineEntry[]>(() => toTimelineEntries(initialArtifacts));
  const [latestEvents, setLatestEvents] = useState<AiRunEvent[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [running, setRunning] = useState(false);
  const [runStatus, setRunStatus] = useState("READY");
  const [stallTip, setStallTip] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const codeContextRef = useRef<CodeContextDetail>({
    questionId,
    questionTitle,
    questionContent,
    language: "java",
    code: ""
  });
  const judgeResultRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [entries, latestEvents, running]);

  const recentEvents = useMemo(() => latestEvents.slice(-4), [latestEvents]);

  const loadRunSnapshot = useCallback(async (runId: string) => {
    const [artifactsResponse, eventsResponse] = await Promise.all([
      fetch(appApiPath(`/ai/runs/${runId}/artifacts`), { cache: "no-store" }),
      fetch(appApiPath(`/ai/runs/${runId}/events`), { cache: "no-store" })
    ]);

    if (!artifactsResponse.ok) {
      throw new Error("Failed to load run artifacts.");
    }
    if (!eventsResponse.ok) {
      throw new Error("Failed to load run events.");
    }

    const [artifacts, eventText] = await Promise.all([
      artifactsResponse.json() as Promise<AiArtifact[]>,
      eventsResponse.text()
    ]);

    setEntries((current) => mergeArtifacts(current, artifacts));
    setLatestEvents(parseRunEvents(eventText));
  }, []);

  const executeRun = useCallback(
    async (userMessage: string, runType: RunType) => {
      if (frontendPreviewMode) {
        const previewArtifact = buildErrorArtifact(
          `当前是前端预览模式，AI 面板不会真正调用后端。你刚才的请求是「${userMessage}」，现在只保留界面和交互走查。`
        );
        previewArtifact.title = "Preview Response";
        previewArtifact.summary = `预览模式下已拦截 ${runType} 请求。`;
        previewArtifact.body.nextAction = "如果要联调真实 AI 能力，请关闭前端预览模式并接通本地后端。";
        setRunStatus("PREVIEW");
        setEntries((current) => mergeArtifacts(current, [previewArtifact]));
        setLatestEvents([]);
        return {
          runId: "preview-run",
          status: "PREVIEW",
          entryGraph: runType,
          eventsUrl: "",
          artifactsUrl: ""
        } satisfies AiRunCreateResponse;
      }

      const response = await fetch(appApiPath("/ai/runs"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          runType,
          source: "workspace_panel",
          context: {
            questionId: codeContextRef.current.questionId ?? questionId,
            questionTitle: codeContextRef.current.questionTitle ?? questionTitle,
            questionContent: codeContextRef.current.questionContent ?? questionContent,
            userCode: codeContextRef.current.code,
            judgeResult: judgeResultRef.current,
            userMessage
          }
        })
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message ?? "Agent run failed.");
      }

      const run = (await response.json()) as AiRunCreateResponse;
      setRunStatus(run.status);
      await loadRunSnapshot(run.runId);
      return run;
    },
    [loadRunSnapshot, questionContent, questionId, questionTitle]
  );

  const submitPrompt = useCallback(
    async (text: string, runType: RunType = "interactive_tutor") => {
      const prompt = text.trim();
      if (!prompt || running) return;

      setEntries((current) => [
        ...current,
        { id: `prompt-${Date.now()}`, kind: "prompt", content: prompt }
      ]);
      setInputValue("");
      setRunning(true);
      setRunStatus("RUNNING");

      try {
        await executeRun(prompt, runType);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Agent run failed.";
        setEntries((current) => mergeArtifacts(current, [buildErrorArtifact(message)]));
        setLatestEvents([]);
        setRunStatus("FAILED");
      } finally {
        setRunning(false);
      }
    },
    [executeRun, running]
  );

  useEffect(() => {
    const codeContextHandler = (event: Event) => {
      const detail = (event as CustomEvent<CodeContextDetail>).detail;
      if (detail?.questionId && questionId && detail.questionId !== questionId) return;
      codeContextRef.current = detail;
    };

    const aiPromptHandler = (event: Event) => {
      const detail = (event as CustomEvent<{ prompt?: string; runType?: RunType }>).detail;
      if (!detail?.prompt) return;
      void submitPrompt(detail.prompt, detail.runType ?? "interactive_tutor");
    };

    const stallHandler = () => setStallTip(true);

    const judgeResultHandler = (event: Event) => {
      const detail = (event as CustomEvent<JudgeResultDetail>).detail;
      if (detail?.questionId && questionId && detail.questionId !== questionId) return;
      judgeResultRef.current = detail.message ? `${detail.status}: ${detail.message}` : detail.status;
    };

    window.addEventListener("syncode:code-context", codeContextHandler);
    window.addEventListener("syncode:ai-prompt", aiPromptHandler);
    window.addEventListener("syncode:edit-stall", stallHandler);
    window.addEventListener("syncode:judge-result", judgeResultHandler);

    return () => {
      window.removeEventListener("syncode:code-context", codeContextHandler);
      window.removeEventListener("syncode:ai-prompt", aiPromptHandler);
      window.removeEventListener("syncode:edit-stall", stallHandler);
      window.removeEventListener("syncode:judge-result", judgeResultHandler);
    };
  }, [questionId, submitPrompt]);

  return (
    <div className="flex h-full flex-col bg-[var(--surface-1)]">
      <div className="shrink-0 border-b border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
        <div>
          <p className="kicker">提问</p>
          <h3 className="mt-0.5 text-base font-semibold text-[var(--text-primary)]">助手</h3>
        </div>
        <div className="mt-2 inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
          <span className={`inline-block h-1.5 w-1.5 rounded-full ${running ? "animate-pulse bg-[var(--accent)]" : "bg-green-500"}`} />
          {running ? "处理中" : null}
        </div>
      </div>

      {stallTip ? (
        <div className="mx-4 mt-3 flex shrink-0 items-start gap-3 rounded-[10px] border border-[var(--accent)]/25 bg-[var(--accent-bg)] px-4 py-3">
          <Sparkles size={14} className="mt-0.5 shrink-0 text-[var(--accent)]" />
          <div className="min-w-0 flex-1">
            <button
              type="button"
              className="text-[11px] font-semibold text-[var(--accent)] hover:underline"
              onClick={() => {
                setStallTip(false);
                void submitPrompt("先给我一点提示，不要直接给完整答案。", "interactive_tutor");
              }}
            >
              先来一个提示
            </button>
          </div>
          <button
            type="button"
            onClick={() => setStallTip(false)}
            className="shrink-0 text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
          >
            <X size={12} />
          </button>
        </div>
      ) : null}

      {recentEvents.length > 0 ? (
        <div className="mx-4 mt-3 shrink-0 rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">本轮进度</p>
          <div className="mt-2 space-y-1.5">
            {recentEvents.map((event) => (
              <div key={event.eventId} className="flex items-start gap-2 text-[11px] text-[var(--text-secondary)]">
                <span className="mt-1 inline-block h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
                <span>{formatEventLabel(event)}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div ref={scrollRef} className="flex-1 divide-y divide-[var(--border-soft)] overflow-auto px-4">
        {entries.length === 0 && !running ? (
          <div data-testid="ai-empty-state" className="py-8">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">开始提问</p>
          </div>
        ) : null}

        {entries.map((entry) =>
          entry.kind === "prompt" ? (
            <PromptBubble key={entry.id} content={entry.content} />
          ) : (
            <ArtifactCard key={entry.id} artifact={entry.artifact} />
          )
        )}
      </div>

      <div className="shrink-0 border-t border-[var(--border-soft)] bg-[var(--surface-1)] px-4 pb-2 pt-3">
        <div className="mb-3 flex flex-wrap gap-1.5">
          {QUICK_ACTIONS.map((item) => (
            <Button
              key={item.label}
              size="sm"
              variant="secondary"
              className="h-7 rounded-[8px] text-[11px]"
              onClick={() => void submitPrompt(item.label, item.runType)}
              disabled={running}
            >
              {item.label}
            </Button>
          ))}
        </div>

        <div className="flex items-end gap-2">
          <textarea
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void submitPrompt(inputValue, "interactive_tutor");
              }
            }}
            placeholder="输入你当前卡住的问题。回车发送，Shift + 回车换行。"
            rows={2}
            className="flex-1 resize-none rounded-[8px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-[13px] leading-relaxed text-[var(--text-primary)] placeholder:text-[var(--text-muted)] transition-colors focus:border-[var(--accent)]/50 focus:outline-none"
          />
          <Button
            size="sm"
            className="h-9 w-9 shrink-0 bg-[var(--accent)] p-0 text-white hover:opacity-90"
            onClick={() => void submitPrompt(inputValue, "interactive_tutor")}
            disabled={running || !inputValue.trim()}
          >
            <Send size={13} />
          </Button>
        </div>
      </div>
    </div>
  );
}
