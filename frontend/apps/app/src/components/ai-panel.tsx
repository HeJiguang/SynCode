"use client";

import * as React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  AiArtifact,
  AiConversation,
  AiConversationSnapshot,
  AiMemoryItem,
  AiRunCreateResponse,
  AiRunEvent,
  AiToolApproval,
  CodeLanguage
} from "@aioj/api";
import { frontendPreviewMode } from "@aioj/config";
import {
  AlertTriangle,
  Ban,
  Check,
  Code2,
  Copy,
  Download,
  History,
  LoaderCircle,
  MessageSquarePlus,
  Send,
  ShieldAlert,
  Sparkles,
  X
} from "lucide-react";

import type { JudgeResultDetail } from "../lib/judge-result";
import { appApiPath, appPublicPath } from "../lib/paths";
import { Button } from "@aioj/ui";


type AiPanelProps = {
  initialArtifacts?: AiArtifact[];
  demoMode?: boolean;
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
  selectedCode?: string;
};

type RunType =
  | "interactive_tutor"
  | "interactive_diagnosis"
  | "interactive_recommendation"
  | "interactive_review"
  | "interactive_plan";

type TimelineEntry =
  | { id: string; kind: "prompt"; content: string; questionTitle?: string | null }
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

type Recommendation = {
  questionId: string;
  title: string;
  reason: string;
  difficulty?: number | string | null;
  knowledgeTags?: string | null;
  estimatedMinutes?: number | null;
};

function artifactRecommendations(artifact: AiArtifact): Recommendation[] {
  if (artifact.artifactType !== "recommendation_pack") return [];
  const payload = artifact.body.responsePayload;
  if (!payload || typeof payload !== "object") return [];
  const raw = (payload as Record<string, unknown>).recommendations;
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((item): Recommendation[] => {
    if (!item || typeof item !== "object") return [];
    const row = item as Record<string, unknown>;
    if (typeof row.questionId !== "string" || !/^\d+$/.test(row.questionId) || typeof row.title !== "string") return [];
    return [{
      questionId: row.questionId,
      title: row.title,
      reason: typeof row.reason === "string" ? row.reason : "",
      difficulty: typeof row.difficulty === "string" || typeof row.difficulty === "number" ? row.difficulty : null,
      knowledgeTags: typeof row.knowledgeTags === "string" ? row.knowledgeTags : null,
      estimatedMinutes: typeof row.estimatedMinutes === "number" ? row.estimatedMinutes : null
    }];
  });
}

function recordRecommendationEvent(runId: string, questionId: string, action: "impression" | "click") {
  if (!/^run_[a-f0-9]+$/.test(runId)) return;
  void fetch(appApiPath(`/ai/runs/${runId}/recommendations/${questionId}/${action}`), {
    method: "POST",
    keepalive: true
  }).catch(() => undefined);
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

function snapshotToTimelineEntries(snapshot: AiConversationSnapshot): TimelineEntry[] {
  return snapshot.messages.flatMap((message): TimelineEntry[] => {
    if (message.role === "USER") {
      const questionTitle = typeof message.contextSnapshot.questionTitle === "string"
        ? message.contextSnapshot.questionTitle
        : null;
      return [{ id: message.messageId, kind: "prompt", content: message.content, questionTitle }];
    }
    if (message.role !== "ASSISTANT") return [];
    const artifact = message.artifact ?? {
      artifactId: `message-${message.messageId}`,
      runId: message.runId ?? "persisted-message",
      artifactType: "answer_card" as const,
      title: message.status === "FAILED" ? "回答失败" : "助手回答",
      body: { answer: message.content },
      renderHint: "markdown" as const,
      version: 1,
      createdAt: message.createdAt
    };
    return [{ id: message.messageId, kind: "artifact", artifact }];
  });
}

function formatTokenCount(value: number) {
  if (value < 1000) return String(value);
  return `${(value / 1000).toFixed(value < 10000 ? 1 : 0)}k`;
}

function formatConversationTime(value?: string | null) {
  if (!value) return "暂无消息";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return "暂无消息";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(parsed);
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

function PromptBubble({ content, questionTitle }: { content: string; questionTitle?: string | null }) {
  return (
    <div className="-mx-4 border-b border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">Query</p>
        {questionTitle ? <p className="truncate text-[10px] text-[var(--text-muted)]">{questionTitle}</p> : null}
      </div>
      <p className="mt-2 text-sm leading-6 text-[var(--text-primary)]">{content}</p>
    </div>
  );
}

function ToolApprovalRow({
  approval,
  pending,
  onDecision
}: {
  approval: AiToolApproval;
  pending: boolean;
  onDecision: (approvalId: string, action: "approve" | "deny") => void;
}) {
  const commitSha = typeof approval.arguments.commit_sha === "string" ? approval.arguments.commit_sha : null;
  const fileCount = typeof approval.result?.fileCount === "number" ? approval.result.fileCount : null;
  const isPending = approval.status === "PENDING";
  const isBlocked = approval.status === "DENIED" || approval.decision === "BLOCK";

  return (
    <div className="mt-4 border-y border-[var(--border-soft)] bg-[var(--surface-1)] px-3 py-3">
      <div className="flex items-start gap-2.5">
        {isBlocked ? (
          <Ban size={15} className="mt-0.5 shrink-0 text-[var(--danger)]" />
        ) : approval.status === "EXECUTED" ? (
          <Check size={15} className="mt-0.5 shrink-0 text-[var(--success)]" />
        ) : (
          <ShieldAlert size={15} className="mt-0.5 shrink-0 text-[var(--warning)]" />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-[var(--text-primary)]">
            {approval.toolName === "github.download_snapshot" ? "GitHub 仓库快照" : approval.toolName}
          </p>
          {approval.resource ? <p className="mt-1 break-all text-[11px] text-[var(--text-secondary)]">{approval.resource}</p> : null}
          {commitSha ? <p className="mt-1 break-all font-mono text-[10px] text-[var(--text-muted)]">commit {commitSha}</p> : null}
          {isPending && approval.expiresAt ? (
            <p className="mt-1 text-[10px] text-[var(--text-muted)]">有效期至 {formatConversationTime(approval.expiresAt)}</p>
          ) : null}
          <p className="mt-2 text-[11px] leading-5 text-[var(--text-muted)]">
            {approval.status === "EXECUTED"
              ? `只读快照已创建${fileCount === null ? "" : `，共 ${fileCount} 个文件`}，未执行任何代码。`
              : isBlocked
                ? approval.reason ?? "该工具请求已被安全策略阻止。"
                : "单次授权 · 不含依赖安装或代码执行"}
          </p>
        </div>
      </div>
      {isPending ? (
        <div className="mt-3 flex justify-end gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => onDecision(approval.approvalId, "deny")}
            disabled={pending}
          >
            拒绝
          </Button>
          <Button size="sm" onClick={() => onDecision(approval.approvalId, "approve")} disabled={pending}>
            {pending ? <LoaderCircle size={13} className="animate-spin" /> : <Download size={13} />}
            单次允许
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function ArtifactCard({
  artifact,
  toolApprovals,
  pendingApprovalId,
  onApprovalDecision
}: {
  artifact: AiArtifact;
  toolApprovals: AiToolApproval[];
  pendingApprovalId: string | null;
  onApprovalDecision: (approvalId: string, action: "approve" | "deny") => void;
}) {
  const answer = artifactText(artifact, "answer");
  const nextAction = artifactText(artifact, "nextAction");
  const intent = artifactText(artifact, "intent");
  const blocks = parseBlocks(answer);
  const recommendations = artifactRecommendations(artifact);

  useEffect(() => {
    if (recommendations.length === 0) return;
    for (const item of recommendations) recordRecommendationEvent(artifact.runId, item.questionId, "impression");
  }, [artifact.runId, artifact.artifactId]);

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

      {recommendations.length > 0 ? (
        <div className="mt-4 grid gap-2" aria-label="推荐练习题">
          {recommendations.map((item) => (
            <div key={item.questionId} className="rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-1)] px-3 py-3">
              <p className="text-sm font-semibold text-[var(--text-primary)]">{item.title}</p>
              {item.reason ? <p className="mt-1 text-xs leading-5 text-[var(--text-secondary)]">{item.reason}</p> : null}
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-[11px] text-[var(--text-muted)]">
                  {[item.knowledgeTags, item.estimatedMinutes ? `约 ${item.estimatedMinutes} 分钟` : null].filter(Boolean).join(" · ")}
                </span>
                <a
                  href={appPublicPath(`/workspace/${encodeURIComponent(item.questionId)}`)}
                  onClick={() => recordRecommendationEvent(artifact.runId, item.questionId, "click")}
                  className="shrink-0 text-xs font-semibold text-[var(--accent)] hover:underline"
                >
                  去做这题 →
                </a>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {toolApprovals.map((approval) => (
        <ToolApprovalRow
          key={approval.approvalId}
          approval={approval}
          pending={pendingApprovalId === approval.approvalId}
          onDecision={onApprovalDecision}
        />
      ))}
    </div>
  );
}

export function AiPanel({
  initialArtifacts = [],
  demoMode = false,
  questionId,
  questionTitle,
  questionContent
}: AiPanelProps) {
  const [entries, setEntries] = useState<TimelineEntry[]>(() => toTimelineEntries(initialArtifacts));
  const [conversationSnapshot, setConversationSnapshot] = useState<AiConversationSnapshot | null>(null);
  const [conversations, setConversations] = useState<AiConversation[]>([]);
  const [toolApprovals, setToolApprovals] = useState<AiToolApproval[]>([]);
  const [latestEvents, setLatestEvents] = useState<AiRunEvent[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [running, setRunning] = useState(false);
  const [runStatus, setRunStatus] = useState("READY");
  const [stallTip, setStallTip] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(!frontendPreviewMode && !demoMode);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [memoryDialogMode, setMemoryDialogMode] = useState<"create" | "view" | null>(null);
  const [memoryCandidates, setMemoryCandidates] = useState<AiMemoryItem[]>([]);
  const [selectedMemoryIds, setSelectedMemoryIds] = useState<Set<string>>(() => new Set());
  const [creatingConversation, setCreatingConversation] = useState(false);
  const [pendingApprovalId, setPendingApprovalId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const codeContextRef = useRef<CodeContextDetail>({
    questionId,
    questionTitle,
    questionContent,
    language: "java",
    code: ""
  });
  const judgeResultRef = useRef<string | undefined>(undefined);

  const activeConversation = conversationSnapshot?.conversation ?? null;
  const defaultConversation = conversations.find((item) => item.isDefault) ??
    (activeConversation?.isDefault ? activeConversation : null);
  const isReadOnly = Boolean(activeConversation && (!activeConversation.isDefault || activeConversation.status !== "ACTIVE"));
  const contextPercent = activeConversation
    ? Math.min(100, Math.round((activeConversation.contextTokenEstimate / activeConversation.hardTokenLimit) * 100))
    : 0;

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [entries, latestEvents, running]);

  const recentEvents = useMemo(() => latestEvents.slice(-4), [latestEvents]);

  const fetchToolApprovals = useCallback(async (conversationId: string) => {
    const response = await fetch(
      appApiPath(`/ai/tool-approvals?conversationId=${encodeURIComponent(conversationId)}`),
      { cache: "no-store" }
    );
    const payload = (await response.json().catch(() => null)) as (AiToolApproval[] & { message?: string }) | null;
    if (!response.ok || !Array.isArray(payload)) {
      throw new Error((payload as { message?: string } | null)?.message ?? "加载工具审批失败。");
    }
    return payload;
  }, []);

  const loadConversation = useCallback(async (conversationId: string) => {
    setLoadingConversation(true);
    setLoadError(null);
    try {
      const [response, approvals] = await Promise.all([
        fetch(appApiPath(`/ai/conversations/${encodeURIComponent(conversationId)}`), { cache: "no-store" }),
        fetchToolApprovals(conversationId)
      ]);
      const payload = (await response.json().catch(() => null)) as (AiConversationSnapshot & { message?: string }) | null;
      if (!response.ok || !payload?.conversation) {
        throw new Error(payload?.message ?? "加载 AI 对话失败。");
      }
      setConversationSnapshot(payload);
      setToolApprovals(approvals);
      setEntries(snapshotToTimelineEntries(payload));
      setLatestEvents([]);
      setHistoryOpen(false);
      return payload;
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "加载 AI 对话失败。");
      return null;
    } finally {
      setLoadingConversation(false);
    }
  }, [fetchToolApprovals]);

  const refreshConversationList = useCallback(async () => {
    const response = await fetch(appApiPath("/ai/conversations"), { cache: "no-store" });
    const payload = (await response.json().catch(() => null)) as (AiConversation[] & { message?: string }) | null;
    if (!response.ok || !Array.isArray(payload)) {
      throw new Error((payload as { message?: string } | null)?.message ?? "加载 Chat 历史失败。");
    }
    setConversations(payload);
    return payload;
  }, []);

  useEffect(() => {
    if (frontendPreviewMode || demoMode) {
      setLoadingConversation(false);
      return;
    }

    let cancelled = false;
    const bootstrap = async () => {
      setLoadingConversation(true);
      setLoadError(null);
      try {
        const snapshotResponse = await fetch(appApiPath("/ai/conversations/default"), { cache: "no-store" });
        const snapshot = (await snapshotResponse.json().catch(() => null)) as (AiConversationSnapshot & { message?: string }) | null;
        if (!snapshotResponse.ok || !snapshot?.conversation) {
          throw new Error(snapshot?.message ?? "加载默认 AI 对话失败。");
        }
        const [historyResponse, approvals] = await Promise.all([
          fetch(appApiPath("/ai/conversations"), { cache: "no-store" }),
          fetchToolApprovals(snapshot.conversation.conversationId)
        ]);
        const history = (await historyResponse.json().catch(() => null)) as (AiConversation[] & { message?: string }) | null;
        if (!historyResponse.ok || !Array.isArray(history)) {
          throw new Error((history as { message?: string } | null)?.message ?? "加载 Chat 历史失败。");
        }
        if (cancelled) return;
        setConversationSnapshot(snapshot);
        setConversations(history.some((item) => item.conversationId === snapshot.conversation.conversationId)
          ? history
          : [snapshot.conversation, ...history]);
        setToolApprovals(approvals);
        setEntries(snapshot.messages.length > 0 ? snapshotToTimelineEntries(snapshot) : toTimelineEntries(initialArtifacts));
      } catch (error) {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : "加载 AI 对话失败。");
        }
      } finally {
        if (!cancelled) setLoadingConversation(false);
      }
    };

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [demoMode, fetchToolApprovals, initialArtifacts]);

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

  const openNewConversationReview = useCallback(async () => {
    const source = defaultConversation;
    if (!source) return;
    setLoadError(null);
    try {
      const response = await fetch(
        appApiPath(`/ai/conversations/${encodeURIComponent(source.conversationId)}/memory-candidates`),
        { cache: "no-store" }
      );
      const payload = (await response.json().catch(() => null)) as (AiMemoryItem[] & { message?: string }) | null;
      if (!response.ok || !Array.isArray(payload)) {
        throw new Error((payload as { message?: string } | null)?.message ?? "加载可继承记忆失败。");
      }
      setMemoryCandidates(payload);
      setSelectedMemoryIds(new Set());
      setMemoryDialogMode("create");
      setHistoryOpen(false);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "加载可继承记忆失败。");
    }
  }, [defaultConversation]);

  const createConversation = useCallback(async () => {
    if (!defaultConversation || creatingConversation) return;
    setCreatingConversation(true);
    setLoadError(null);
    try {
      const response = await fetch(appApiPath("/ai/conversations"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "新的学习对话",
          continuedFromConversationId: defaultConversation.conversationId,
          memoryIds: [...selectedMemoryIds]
        })
      });
      const payload = (await response.json().catch(() => null)) as (AiConversationSnapshot & { message?: string }) | null;
      if (!response.ok || !payload?.conversation) {
        throw new Error(payload?.message ?? "创建 AI 对话失败。");
      }
      setConversationSnapshot(payload);
      setToolApprovals([]);
      setEntries(snapshotToTimelineEntries(payload));
      setLatestEvents([]);
      setMemoryDialogMode(null);
      await refreshConversationList();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "创建 AI 对话失败。");
    } finally {
      setCreatingConversation(false);
    }
  }, [creatingConversation, defaultConversation, refreshConversationList, selectedMemoryIds]);

  const decideToolApproval = useCallback(async (approvalId: string, action: "approve" | "deny") => {
    if (pendingApprovalId) return;
    setPendingApprovalId(approvalId);
    setLoadError(null);
    try {
      const response = await fetch(
        appApiPath(`/ai/tool-approvals/${encodeURIComponent(approvalId)}/${action}`),
        { method: "POST" }
      );
      const payload = (await response.json().catch(() => null)) as (AiToolApproval & { message?: string }) | null;
      if (!response.ok || !payload?.approvalId) {
        throw new Error(payload?.message ?? "处理工具审批失败。");
      }
      const runResponse = await fetch(appApiPath(`/ai/runs/${encodeURIComponent(payload.runId)}`), {
        cache: "no-store"
      });
      const run = (await runResponse.json().catch(() => null)) as { status?: string; message?: string } | null;
      if (!runResponse.ok || !run?.status) {
        throw new Error(run?.message ?? "加载审批后的运行状态失败。");
      }
      if (payload.conversationId) {
        await loadConversation(payload.conversationId);
      }
      await loadRunSnapshot(payload.runId);
      await refreshConversationList();
      setRunStatus(run.status);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "处理工具审批失败。");
    } finally {
      setPendingApprovalId(null);
    }
  }, [loadConversation, loadRunSnapshot, pendingApprovalId, refreshConversationList]);

  const executeRun = useCallback(
    async (userMessage: string, runType: RunType) => {
      if (frontendPreviewMode || demoMode) {
        const previewArtifact = buildErrorArtifact(
          demoMode
            ? `测试体验模式不会调用真实 AI 服务。你刚才的请求是「${userMessage}」。`
            : `当前是前端预览模式，AI 面板不会真正调用后端。你刚才的请求是「${userMessage}」，现在只保留界面和交互走查。`
        );
        previewArtifact.title = demoMode ? "测试体验提示" : "Preview Response";
        previewArtifact.summary = `${demoMode ? "测试体验" : "预览"}模式下已拦截 ${runType} 请求。`;
        previewArtifact.body.nextAction = demoMode ? "正式登录后可使用真实 AI 辅助能力。" : "如果要联调真实 AI 能力，请关闭前端预览模式并接通本地后端。";
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
          conversationId: activeConversation?.conversationId,
          context: {
            questionId: codeContextRef.current.questionId ?? questionId,
            questionTitle: codeContextRef.current.questionTitle ?? questionTitle,
            questionContent: codeContextRef.current.questionContent ?? questionContent,
            userCode: codeContextRef.current.code,
            selectedCode: codeContextRef.current.selectedCode,
            language: codeContextRef.current.language,
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
      const persistedConversationId = run.conversationId ?? activeConversation?.conversationId;
      if (persistedConversationId) {
        await loadConversation(persistedConversationId);
        await refreshConversationList();
      }
      return run;
    },
    [activeConversation?.conversationId, demoMode, loadConversation, loadRunSnapshot, questionContent, questionId, questionTitle, refreshConversationList]
  );

  const submitPrompt = useCallback(
    async (text: string, runType: RunType = "interactive_tutor") => {
      const prompt = text.trim();
      if (!prompt || running || loadingConversation || isReadOnly || activeConversation?.hardLimitReached) return;

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
    [activeConversation?.hardLimitReached, executeRun, isReadOnly, loadingConversation, running]
  );

  useEffect(() => {
    const codeContextHandler = (event: Event) => {
      const detail = (event as CustomEvent<CodeContextDetail>).detail;
      if (detail?.questionId && questionId && detail.questionId !== questionId) return;
      codeContextRef.current = detail;
    };

    const aiPromptHandler = (event: Event) => {
      const detail = (event as CustomEvent<{ prompt?: string; runType?: RunType; selectedCode?: string }>).detail;
      if (!detail?.prompt) return;
      codeContextRef.current.selectedCode = detail.selectedCode;
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
    <div className="relative flex h-full flex-col bg-[var(--surface-1)]">
      <div className="shrink-0 border-b border-[var(--border-soft)] bg-[var(--surface-1)] px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="kicker">提问</p>
            <h3 className="mt-0.5 truncate text-base font-semibold text-[var(--text-primary)]">
              {activeConversation?.title ?? "助手"}
            </h3>
          </div>
          {!frontendPreviewMode && !demoMode ? (
            <div className="flex shrink-0 items-center gap-1">
              {conversationSnapshot?.contextMemories.length ? (
                <button
                  type="button"
                  title="查看本 Chat 的记忆"
                  aria-label="查看本 Chat 的记忆"
                  onClick={() => setMemoryDialogMode("view")}
                  className="flex h-8 min-w-8 items-center justify-center rounded-[6px] px-2 text-[11px] font-semibold text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text-primary)]"
                >
                  记忆 {conversationSnapshot.contextMemories.length}
                </button>
              ) : null}
              <button
                type="button"
                title="Chat 历史"
                aria-label="Chat 历史"
                onClick={() => setHistoryOpen(true)}
                className="flex h-8 w-8 items-center justify-center rounded-[6px] text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text-primary)]"
              >
                <History size={15} />
              </button>
              <button
                type="button"
                title="新建 Chat"
                aria-label="新建 Chat"
                onClick={() => void openNewConversationReview()}
                disabled={!defaultConversation || running}
                className="flex h-8 w-8 items-center justify-center rounded-[6px] text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-40"
              >
                <MessageSquarePlus size={15} />
              </button>
            </div>
          ) : null}
        </div>
        <div className="mt-2 flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <span className={`inline-block h-1.5 w-1.5 rounded-full ${running ? "animate-pulse bg-[var(--accent)]" : loadError ? "bg-[var(--danger)]" : "bg-green-500"}`} />
          <span>{running ? "处理中" : loadingConversation ? "同步中" : isReadOnly ? "历史 Chat" : "就绪"}</span>
          {activeConversation ? (
            <span className="ml-auto tabular-nums">
              {formatTokenCount(activeConversation.contextTokenEstimate)} / {formatTokenCount(activeConversation.hardTokenLimit)}
            </span>
          ) : null}
        </div>
        {activeConversation ? (
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-[var(--surface-3)]" aria-label={`上下文已使用 ${contextPercent}%`}>
            <div
              className={`h-full transition-[width] ${activeConversation.rolloverRecommended ? "bg-[var(--warning)]" : "bg-[var(--accent)]"}`}
              style={{ width: `${contextPercent}%` }}
            />
          </div>
        ) : null}
      </div>

      {loadError ? (
        <div className="flex shrink-0 items-start gap-2 border-b border-[var(--danger)]/30 bg-[var(--danger-bg)] px-4 py-2.5 text-xs leading-5 text-[var(--danger)]">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span className="min-w-0 flex-1">{loadError}</span>
          <button type="button" aria-label="关闭错误提示" onClick={() => setLoadError(null)}>
            <X size={13} />
          </button>
        </div>
      ) : null}

      {activeConversation?.rolloverRecommended || isReadOnly ? (
        <div className="flex shrink-0 items-center gap-2 border-b border-[var(--border-soft)] bg-[var(--warning-bg)] px-4 py-2.5 text-xs text-[var(--text-secondary)]">
          <AlertTriangle size={14} className="shrink-0 text-[var(--warning)]" />
          <span className="min-w-0 flex-1">
            {isReadOnly
              ? "这是历史 Chat，只能查看。"
              : activeConversation?.hardLimitReached
                ? "当前 Chat 已达到上下文上限。"
                : "当前 Chat 的上下文即将达到上限。"}
          </span>
          <button
            type="button"
            onClick={() => void openNewConversationReview()}
            className="shrink-0 font-semibold text-[var(--accent)] hover:underline"
          >
            新 Chat
          </button>
        </div>
      ) : null}

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
        {loadingConversation ? (
          <div className="flex items-center justify-center gap-2 py-8 text-xs text-[var(--text-muted)]">
            <LoaderCircle size={14} className="animate-spin" />
            正在同步 Chat
          </div>
        ) : null}
        {entries.length === 0 && !running ? (
          <div data-testid="ai-empty-state" className="py-8">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">开始提问</p>
          </div>
        ) : null}

        {entries.map((entry) =>
          entry.kind === "prompt" ? (
            <PromptBubble key={entry.id} content={entry.content} questionTitle={entry.questionTitle} />
          ) : (
            <ArtifactCard
              key={entry.id}
              artifact={entry.artifact}
              toolApprovals={toolApprovals.filter((approval) => approval.runId === entry.artifact.runId)}
              pendingApprovalId={pendingApprovalId}
              onApprovalDecision={(approvalId, action) => void decideToolApproval(approvalId, action)}
            />
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
              disabled={running || loadingConversation || isReadOnly || activeConversation?.hardLimitReached}
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
            disabled={loadingConversation || isReadOnly || activeConversation?.hardLimitReached}
            className="flex-1 resize-none rounded-[8px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-[13px] leading-relaxed text-[var(--text-primary)] placeholder:text-[var(--text-muted)] transition-colors focus:border-[var(--accent)]/50 focus:outline-none"
          />
          <Button
            size="sm"
            className="h-9 w-9 shrink-0 bg-[var(--accent)] p-0 text-white hover:opacity-90"
            onClick={() => void submitPrompt(inputValue, "interactive_tutor")}
            disabled={running || loadingConversation || isReadOnly || activeConversation?.hardLimitReached || !inputValue.trim()}
            title="发送"
            aria-label="发送"
          >
            <Send size={13} />
          </Button>
        </div>
      </div>

      {historyOpen ? (
        <div className="absolute inset-0 z-30 flex flex-col bg-[var(--surface-1)]">
          <div className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--border-soft)] px-4">
            <div>
              <p className="text-sm font-semibold text-[var(--text-primary)]">Chat 历史</p>
              <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">{conversations.length} 个对话</p>
            </div>
            <button
              type="button"
              title="关闭"
              aria-label="关闭 Chat 历史"
              onClick={() => setHistoryOpen(false)}
              className="flex h-8 w-8 items-center justify-center rounded-[6px] text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text-primary)]"
            >
              <X size={15} />
            </button>
          </div>
          <div className="flex-1 overflow-auto">
            {conversations.map((conversation) => (
              <button
                type="button"
                key={conversation.conversationId}
                onClick={() => void loadConversation(conversation.conversationId)}
                className={`block w-full border-b border-[var(--border-soft)] px-4 py-3 text-left transition-colors hover:bg-[var(--surface-2)] ${
                  conversation.conversationId === activeConversation?.conversationId ? "border-l-2 border-l-[var(--accent)] bg-[var(--surface-2)]" : ""
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate text-sm font-semibold text-[var(--text-primary)]">{conversation.title}</span>
                  {conversation.isDefault ? <span className="text-[10px] font-semibold text-[var(--accent)]">当前</span> : null}
                </div>
                <p className="mt-1 truncate text-xs text-[var(--text-secondary)]">
                  {conversation.currentQuestionTitle ?? "尚未关联题目"}
                </p>
                <div className="mt-2 flex items-center justify-between text-[10px] text-[var(--text-muted)]">
                  <span>{conversation.messageCount} 条消息</span>
                  <span>{formatConversationTime(conversation.lastMessageAt ?? conversation.updatedAt)}</span>
                </div>
              </button>
            ))}
          </div>
          <div className="shrink-0 border-t border-[var(--border-soft)] p-3">
            <Button className="w-full" onClick={() => void openNewConversationReview()} disabled={!defaultConversation || running}>
              <MessageSquarePlus size={14} />
              新建 Chat
            </Button>
          </div>
        </div>
      ) : null}

      {memoryDialogMode ? (
        <div className="absolute inset-0 z-40 flex items-end bg-black/45">
          <div className="flex max-h-[86%] w-full flex-col border-t border-[var(--border-strong)] bg-[var(--surface-1)]">
            <div className="flex shrink-0 items-start justify-between gap-3 border-b border-[var(--border-soft)] px-4 py-3">
              <div>
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  {memoryDialogMode === "create" ? "选择带入新 Chat 的记忆" : "本 Chat 使用的记忆"}
                </p>
                <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                  {memoryDialogMode === "create" ? `已选择 ${selectedMemoryIds.size} 条` : `${conversationSnapshot?.contextMemories.length ?? 0} 条`}
                </p>
              </div>
              <button
                type="button"
                title="关闭"
                aria-label="关闭记忆审核"
                onClick={() => setMemoryDialogMode(null)}
                className="flex h-8 w-8 items-center justify-center rounded-[6px] text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text-primary)]"
              >
                <X size={15} />
              </button>
            </div>
            <div className="flex-1 overflow-auto">
              {(memoryDialogMode === "create" ? memoryCandidates : conversationSnapshot?.contextMemories ?? []).length === 0 ? (
                <p className="px-4 py-8 text-center text-xs text-[var(--text-muted)]">暂无可用记忆</p>
              ) : (
                (memoryDialogMode === "create" ? memoryCandidates : conversationSnapshot?.contextMemories ?? []).map((memory) => {
                  const checked = selectedMemoryIds.has(memory.memoryId);
                  return (
                    <label key={memory.memoryId} className="flex cursor-pointer items-start gap-3 border-b border-[var(--border-soft)] px-4 py-3">
                      {memoryDialogMode === "create" ? (
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {
                            setSelectedMemoryIds((current) => {
                              const next = new Set(current);
                              if (next.has(memory.memoryId)) next.delete(memory.memoryId);
                              else next.add(memory.memoryId);
                              return next;
                            });
                          }}
                          className="mt-1 h-4 w-4 accent-[var(--accent)]"
                        />
                      ) : (
                        <Check size={15} className="mt-0.5 shrink-0 text-[var(--success)]" />
                      )}
                      <span className="min-w-0 flex-1">
                        <span className="block break-words text-xs font-semibold text-[var(--text-primary)]">{memory.content}</span>
                        {memory.reason ? <span className="mt-1 block text-[11px] leading-5 text-[var(--text-muted)]">{memory.reason}</span> : null}
                        <span className="mt-1 block text-[10px] uppercase text-[var(--text-muted)]">
                          {memory.memoryType} · 可信度 {Math.round(memory.confidence * 100)}%
                        </span>
                      </span>
                    </label>
                  );
                })
              )}
            </div>
            <div className="flex shrink-0 justify-end gap-2 border-t border-[var(--border-soft)] p-3">
              <Button variant="secondary" onClick={() => setMemoryDialogMode(null)} disabled={creatingConversation}>
                取消
              </Button>
              {memoryDialogMode === "create" ? (
                <Button onClick={() => void createConversation()} disabled={creatingConversation}>
                  {creatingConversation ? <LoaderCircle size={14} className="animate-spin" /> : <MessageSquarePlus size={14} />}
                  创建 Chat
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
