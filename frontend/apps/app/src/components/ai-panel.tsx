"use client";

import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { AiMessage, CodeLanguage } from "@aioj/api";
import { Check, Code2, Copy, Send, Sparkles, X } from "lucide-react";

import type { JudgeResultDetail } from "../lib/judge-result";
import { appApiPath } from "../lib/paths";
import { Button, Panel } from "@aioj/ui";

type AiPanelProps = {
  messages: AiMessage[];
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

function normalizeStreamChunk(chunk: string) {
  return chunk
    .replace(/\r/g, "")
    .split("\n")
    .map((line) => line.replace(/^data:\s?/, ""))
    .filter((line) => line !== "[DONE]" && !line.startsWith("event:") && !line.startsWith(":"))
    .join("\n");
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
      <div className="flex items-center justify-between border-b border-white/5 bg-black/30 px-3 py-1.5">
        <div className="flex items-center gap-1.5">
          <Code2 size={11} className="text-[var(--text-muted)]" />
          <span className="text-[10px] font-mono font-medium uppercase text-[var(--text-muted)]">{lang}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => {
              window.dispatchEvent(new CustomEvent("syncode:insert-code", { detail: { code: content } }));
            }}
            className="rounded px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--accent-bg)] hover:text-[var(--accent)]"
          >
            插入编辑器
          </button>
          <button
            type="button"
            onClick={copy}
            className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text-primary)]"
          >
            {copied ? <Check size={10} className="text-[var(--success)]" /> : <Copy size={10} />}
            {copied ? "已复制" : "复制"}
          </button>
        </div>
      </div>
      <pre className="m-0 overflow-x-auto bg-black/40 p-3 font-mono text-[12px] leading-[1.7] text-zinc-300">
        <code>{content}</code>
      </pre>
    </div>
  );
}

function MessageBubble({ content, role, title }: { content: string; role: AiMessage["role"]; title?: string }) {
  const blocks = parseBlocks(content);

  return (
    <div
      className={
        role === "assistant"
          ? "ai-typewriter-enter -mx-5 border-l-2 border-[var(--accent)] bg-[var(--surface-2)] px-5 py-4 pl-9"
          : "py-4"
      }
    >
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
        {role === "assistant" ? "AI 回复" : "你的提问"}
      </p>
      {title ? <p className="mb-1.5 text-sm font-semibold text-[var(--text-primary)]">{title}</p> : null}
      {blocks.map((block, index) =>
        block.type === "code" ? (
          <CodeBlock key={index} lang={block.lang} content={block.content} />
        ) : (
          <p key={index} className="whitespace-pre-wrap text-sm leading-6 text-[var(--text-secondary)]">
            {block.content}
          </p>
        )
      )}
    </div>
  );
}

export function AiPanel({ messages: initialMessages, questionId, questionTitle, questionContent }: AiPanelProps) {
  const [messages, setMessages] = useState(initialMessages);
  const [inputValue, setInputValue] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [streamingTitle, setStreamingTitle] = useState("");
  const [stallTip, setStallTip] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const codeContextRef = useRef<CodeContextDetail>({
    questionId,
    questionTitle,
    questionContent,
    language: "java",
    code: ""
  });
  const judgeResultRef = useRef("");

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingText]);

  const requestFallbackChat = useCallback(async (userMessage: string) => {
    const response = await fetch(appApiPath("/ai/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        questionTitle: codeContextRef.current.questionTitle ?? questionTitle,
        questionContent: codeContextRef.current.questionContent ?? questionContent,
        userCode: codeContextRef.current.code,
        judgeResult: judgeResultRef.current,
        userMessage
      })
    });

    const payload = (await response.json()) as { content?: string; message?: string };
    if (!response.ok || !payload.content) {
      throw new Error(payload.message ?? "AI 请求失败。");
    }

    return payload.content;
  }, [questionContent, questionTitle]);

  const streamAssistantReply = useCallback(
    async (userMessage: string, title: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setStreaming(true);
      setStreamingTitle(title);
      setStreamingText("");

      try {
        const response = await fetch(appApiPath("/ai/stream"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            questionTitle: codeContextRef.current.questionTitle ?? questionTitle,
            questionContent: codeContextRef.current.questionContent ?? questionContent,
            userCode: codeContextRef.current.code,
            judgeResult: judgeResultRef.current,
            userMessage
          }),
          signal: controller.signal
        });

        if (!response.ok) {
          const payload = (await response.json()) as { message?: string };
          throw new Error(payload.message ?? "AI 流式请求失败。");
        }

        if (!response.body) {
          const fallback = await requestFallbackChat(userMessage);
          setMessages((current) => [
            ...current,
            { id: `ai-${Date.now()}`, role: "assistant", title, content: fallback }
          ]);
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = normalizeStreamChunk(decoder.decode(value, { stream: true }));
          if (!chunk) continue;

          fullText += chunk;
          setStreamingText(fullText);
        }

        if (!fullText.trim()) {
          fullText = await requestFallbackChat(userMessage);
        }

        setMessages((current) => [
          ...current,
          { id: `ai-${Date.now()}`, role: "assistant", title, content: fullText }
        ]);
      } catch (error) {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : "AI 请求失败。";
        setMessages((current) => [
          ...current,
          { id: `ai-${Date.now()}`, role: "assistant", title: "请求失败", content: message }
        ]);
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
        setStreaming(false);
        setStreamingText("");
        setStreamingTitle("");
      }
    },
    [questionContent, questionTitle, requestFallbackChat]
  );

  const submitPrompt = useCallback(
    async (text: string, title = "AI 回答") => {
      const prompt = text.trim();
      if (!prompt || streaming) return;

      setMessages((current) => [
        ...current,
        { id: `user-${Date.now()}`, role: "user", content: prompt }
      ]);
      setInputValue("");
      await streamAssistantReply(prompt, title);
    },
    [streamAssistantReply, streaming]
  );

  useEffect(() => {
    const codeContextHandler = (event: Event) => {
      const detail = (event as CustomEvent<CodeContextDetail>).detail;
      if (detail?.questionId && questionId && detail.questionId !== questionId) return;
      codeContextRef.current = detail;
    };

    const aiPromptHandler = (event: Event) => {
      const detail = (event as CustomEvent<{ prompt?: string; label?: string }>).detail;
      if (!detail?.prompt) return;
      void submitPrompt(detail.prompt, detail.label ?? "AI 分析");
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
    <Panel hoverable className="flex h-full flex-col p-0">
      <div className="shrink-0 border-b border-[var(--border-soft)] px-5 py-4">
        <div>
          <p className="kicker">AI Assistant</p>
          <h3 className="mt-0.5 text-base font-semibold text-[var(--text-primary)]">AI 辅助</h3>
        </div>
        <div className="mt-2 inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
          <span className={`inline-block h-1.5 w-1.5 rounded-full ${streaming ? "animate-pulse bg-[var(--accent)]" : "bg-green-500"}`} />
          {streaming ? "SSE Streaming..." : "Ready"}
        </div>
      </div>

      {stallTip ? (
        <div className="mx-4 mt-3 flex shrink-0 items-start gap-3 rounded-[var(--radius-sm)] border border-[var(--accent)]/25 bg-[var(--accent-bg)] px-4 py-3">
          <Sparkles size={14} className="mt-0.5 shrink-0 text-[var(--accent)]" />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-[var(--text-primary)]">看起来你在这里停留了一会儿</p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-[var(--text-secondary)]">
              我可以先给你一条思路提示，再决定是否展开完整分析。
            </p>
            <button
              type="button"
              className="mt-2 text-[11px] font-semibold text-[var(--accent)] hover:underline"
              onClick={() => {
                setStallTip(false);
                void submitPrompt("请先给我一个不直接给答案的思路提示。", "思路提示");
              }}
            >
              给我一条提示
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

      <div ref={scrollRef} className="flex-1 overflow-auto px-5 divide-y divide-[var(--border-soft)]">
        {messages.length === 0 && !streaming ? (
          <div data-testid="ai-empty-state" className="py-8">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
              No conversation history yet
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
              Ask for a hint, debugging help, or a complexity review to start this workspace conversation.
            </p>
          </div>
        ) : null}

        {messages.map((message) => (
          <MessageBubble key={message.id} role={message.role} title={message.title} content={message.content} />
        ))}

        {streaming && streamingText ? (
          <div className="-mx-5 border-l-2 border-[var(--accent)] bg-[var(--surface-2)] px-5 py-4 pl-9">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">AI 回复</p>
            {streamingTitle ? <p className="mb-1.5 text-sm font-semibold text-[var(--text-primary)]">{streamingTitle}</p> : null}
            <p className="whitespace-pre-wrap text-sm leading-6 text-[var(--text-secondary)]">
              {streamingText}
              <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse align-middle bg-[var(--accent)]" />
            </p>
          </div>
        ) : null}
      </div>

      <div className="shrink-0 border-t border-[var(--border-soft)] px-4 pb-2 pt-3">
        <div className="mb-3 flex flex-wrap gap-1.5">
          {[
            { label: "给我一个解题思路", title: "思路提示" },
            { label: "帮我分析最近一次提交为什么没过", title: "结果分析" },
            { label: "看看这题更优的复杂度写法", title: "复杂度优化" }
          ].map((item) => (
            <Button
              key={item.label}
              size="sm"
              variant="secondary"
              className="h-7 text-[11px]"
              onClick={() => void submitPrompt(item.label, item.title)}
              disabled={streaming}
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
                void submitPrompt(inputValue, "AI 回答");
              }
            }}
            placeholder="向 AI 提问，Enter 发送，Shift+Enter 换行"
            rows={2}
            className="flex-1 resize-none rounded-[var(--radius-sm)] border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-[13px] leading-relaxed text-[var(--text-primary)] placeholder:text-[var(--text-muted)] transition-colors focus:border-[var(--accent)]/50 focus:outline-none"
          />
          <Button
            size="sm"
            className="h-9 w-9 shrink-0 bg-[var(--accent)] p-0 text-white hover:opacity-90"
            onClick={() => void submitPrompt(inputValue, "AI 回答")}
            disabled={streaming || !inputValue.trim()}
          >
            <Send size={13} />
          </Button>
        </div>
      </div>
    </Panel>
  );
}
