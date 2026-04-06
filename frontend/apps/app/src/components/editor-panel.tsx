"use client";

import * as React from "react";
import { startTransition, useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import {
  type CodeLanguage,
  type ExampleCase,
  getBrowserAccessToken,
  isJudgeLanguageSupported,
  resolveJudgeWebSocketUrl
} from "@aioj/api";
import { frontendPreviewMode } from "@aioj/config";
import { CheckCircle2, Loader2, Play, SendHorizontal, Terminal } from "lucide-react";

import { normalizeJudgeOutcome, type JudgeResultDetail } from "../lib/judge-result";
import { appApiPath } from "../lib/paths";
import { Button, Tag, Textarea } from "@aioj/ui";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false
});

type EditorPanelProps = {
  initialCode: Record<CodeLanguage, string>;
  questionId?: string;
  examId?: string;
  questionTitle?: string;
  questionContent?: string;
  examples?: ExampleCase[];
};

type JudgeStage = {
  label: string;
  done?: boolean;
  error?: boolean;
};

type JudgeSubmittedDetail = {
  questionId?: string;
  examId?: string;
  requestId: string;
  language: string;
};

type JudgeSocketPayload = {
  type?: string;
  requestId?: string | null;
  asyncStatus?: number | null;
  pass?: number | null;
  exeMessage?: string | null;
  lastError?: string | null;
  message?: string | null;
};

type RunCaseResult = {
  input?: string;
  expectedOutput?: string | null;
  actualOutput?: string | null;
  passed?: boolean | null;
  custom?: boolean | null;
};

type RunResult = {
  runStatus?: string;
  exeMessage?: string;
  useMemory?: number | null;
  useTime?: number | null;
  caseResults?: RunCaseResult[];
};

const languageLabels: Record<CodeLanguage, string> = {
  java: "Java",
  cpp: "C++",
  python: "Python",
  go: "Go",
  javascript: "JavaScript"
};

const monacoLanguages: Record<CodeLanguage, string> = {
  java: "java",
  cpp: "cpp",
  python: "python",
  go: "go",
  javascript: "javascript"
};

const ghostSnippets: Record<CodeLanguage, Record<string, string>> = {
  java: {
    "for (": "int i = 0; i < n; i++) {\n    \n}",
    "Map<": "Integer, Integer> map = new HashMap<>();",
    "HashMap": "<Integer, Integer> map = new HashMap<>();"
  },
  cpp: {
    "for (": "int i = 0; i < n; i++) {\n    \n}",
    "unordered_map": "<int, int> cache;"
  },
  python: {
    "for i": " in range(len(nums)):\n    ",
    defaultdict: "(int)"
  },
  go: {
    "for i": " := 0; i < len(nums); i++ {\n\t\n}",
    "make(map": "[int]int)"
  },
  javascript: {
    "for (": "let i = 0; i < n; i++) {\n    \n}",
    "new Map": "()"
  }
};

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseCustomInputs(value: string) {
  return value
    .split(/\n\s*---+\s*\n/g)
    .map((item) => item.trim())
    .filter(Boolean);
}

function emitCodeContext(detail: {
  questionId?: string;
  questionTitle?: string;
  questionContent?: string;
  language: CodeLanguage;
  code: string;
}) {
  window.dispatchEvent(new CustomEvent("syncode:code-context", { detail }));
}

function emitJudgeSubmitted(detail: JudgeSubmittedDetail) {
  window.dispatchEvent(new CustomEvent("syncode:judge-submitted", { detail }));
}

function emitJudgeResult(detail: JudgeResultDetail) {
  window.dispatchEvent(new CustomEvent("syncode:judge-result", { detail }));
}

export function EditorPanel({
  initialCode,
  questionId = "unknown",
  examId,
  questionTitle,
  questionContent,
  examples = []
}: EditorPanelProps) {
  const availableLanguages = Object.keys(initialCode) as CodeLanguage[];
  const [language, setLanguage] = useState<CodeLanguage>(availableLanguages[0] ?? "java");
  const [drafts, setDrafts] = useState<Record<CodeLanguage, string>>(initialCode);
  const [mounted, setMounted] = useState(false);
  const [showConsole, setShowConsole] = useState(false);
  const [judgeStage, setJudgeStage] = useState<JudgeStage | null>(null);
  const [customInput, setCustomInput] = useState("");
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [lightTheme, setLightTheme] = useState(false);

  const editorRef = useRef<any>(null);
  const monacoRef = useRef<any>(null);
  const ghostProviderRef = useRef<{ dispose: () => void } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const editCountRef = useRef(0);
  const editTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => {
      if (editTimerRef.current) clearTimeout(editTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: light)");

    const syncTheme = () => {
      const root = document.documentElement;
      const isLight = root.classList.contains("light") || (!root.classList.contains("dark") && media.matches);
      setLightTheme(isLight);
    };

    syncTheme();
    media.addEventListener("change", syncTheme);

    const observer = new MutationObserver(syncTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    return () => {
      media.removeEventListener("change", syncTheme);
      observer.disconnect();
    };
  }, []);

  const activeCode = drafts[language] ?? "";

  useEffect(() => {
    emitCodeContext({
      questionId,
      questionTitle,
      questionContent,
      language,
      code: activeCode
    });
  }, [activeCode, language, questionContent, questionId, questionTitle]);

  const fireAiPrompt = useCallback((prompt: string, label: string) => {
    window.dispatchEvent(
      new CustomEvent("syncode:ai-prompt", {
        detail: {
          prompt,
          label
        }
      })
    );
  }, []);

  const setEditorError = useCallback((line: number, message: string) => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco) return;

    const model = editor.getModel();
    if (!model) return;

    monaco.editor.setModelMarkers(model, "syncode-judge", [
      {
        startLineNumber: line,
        startColumn: 1,
        endLineNumber: line,
        endColumn: model.getLineLength(line) + 1,
        message,
        severity: monaco.MarkerSeverity.Error
      }
    ]);
  }, []);

  const clearEditorErrors = useCallback(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco) return;

    const model = editor.getModel();
    if (!model) return;

    monaco.editor.setModelMarkers(model, "syncode-judge", []);
  }, []);

  const registerGhostText = useCallback((monaco: any, nextLanguage: CodeLanguage) => {
    ghostProviderRef.current?.dispose();
    ghostProviderRef.current = null;

    const snippets = ghostSnippets[nextLanguage] ?? {};
    ghostProviderRef.current = monaco.languages.registerInlineCompletionsProvider(monacoLanguages[nextLanguage], {
      provideInlineCompletions(model: any, position: any) {
        const textBefore = model.getValueInRange({
          startLineNumber: position.lineNumber,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column
        });

        for (const [trigger, completion] of Object.entries(snippets)) {
          if (textBefore.endsWith(trigger)) {
            return {
              items: [
                {
                  insertText: completion,
                  range: {
                    startLineNumber: position.lineNumber,
                    startColumn: position.column,
                    endLineNumber: position.lineNumber,
                    endColumn: position.column
                  }
                }
              ]
            };
          }
        }

        return { items: [] };
      },
      freeInlineCompletions() {}
    });
  }, []);

  const handleInsertCode = useCallback((incomingCode: string) => {
    const editor = editorRef.current;
    if (!editor) return;

    const model = editor.getModel();
    if (!model) return;

    const selection = editor.getSelection();
    if (selection) {
      editor.executeEdits("syncode-ai", [
        {
          range: selection,
          text: incomingCode,
          forceMoveMarkers: true
        }
      ]);
    } else {
      const lastLine = model.getLineCount();
      const lastColumn = model.getLineLength(lastLine) + 1;
      editor.executeEdits("syncode-ai", [
        {
          range: {
            startLineNumber: lastLine,
            startColumn: lastColumn,
            endLineNumber: lastLine,
            endColumn: lastColumn
          },
          text: `\n${incomingCode}`,
          forceMoveMarkers: true
        }
      ]);
    }

    editor.focus();
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ code?: string }>).detail;
      if (!detail?.code) return;
      handleInsertCode(detail.code);
    };

    window.addEventListener("syncode:insert-code", handler);
    return () => window.removeEventListener("syncode:insert-code", handler);
  }, [handleInsertCode]);

  const handleEditorMount = useCallback(
    (editor: any, monaco: any) => {
      editorRef.current = editor;
      monacoRef.current = monaco;

      registerGhostText(monaco, language);

      editor.addAction({
        id: "syncode.ai.explain",
        label: "AI 解释这段逻辑",
        contextMenuGroupId: "syncode",
        contextMenuOrder: 1,
        run(instance: any) {
          const selection = instance.getSelection();
          if (!selection) return;

          const code = instance.getModel()?.getValueInRange(selection) ?? "";
          if (!code.trim()) return;

          fireAiPrompt(
            `请解释下面这段 ${languageLabels[language]} 代码在题目「${questionTitle ?? questionId}」里的作用：\n\`\`\`${language}\n${code}\n\`\`\``,
            "解释代码"
          );
        }
      });

      editor.addAction({
        id: "syncode.ai.debug",
        label: "AI 帮我定位问题",
        contextMenuGroupId: "syncode",
        contextMenuOrder: 2,
        run(instance: any) {
          const selection = instance.getSelection();
          if (!selection) return;

          const code = instance.getModel()?.getValueInRange(selection) ?? "";
          if (!code.trim()) return;

          fireAiPrompt(
            `请帮我检查下面这段 ${languageLabels[language]} 代码可能存在的问题，并给出修改建议：\n\`\`\`${language}\n${code}\n\`\`\``,
            "定位问题"
          );
        }
      });

      editor.addAction({
        id: "syncode.ai.optimize",
        label: "AI 优化复杂度",
        contextMenuGroupId: "syncode",
        contextMenuOrder: 3,
        run(instance: any) {
          const selection = instance.getSelection();
          if (!selection) return;

          const code = instance.getModel()?.getValueInRange(selection) ?? "";
          if (!code.trim()) return;

          fireAiPrompt(
            `请分析下面这段 ${languageLabels[language]} 代码的复杂度，并给出更优写法：\n\`\`\`${language}\n${code}\n\`\`\``,
            "优化复杂度"
          );
        }
      });

      editor.onDidChangeModelContent(() => {
        editCountRef.current += 1;
        if (editTimerRef.current) clearTimeout(editTimerRef.current);
        editTimerRef.current = setTimeout(() => {
          if (editCountRef.current >= 5) {
            window.dispatchEvent(
              new CustomEvent("syncode:edit-stall", {
                detail: { count: editCountRef.current }
              })
            );
          }
          editCountRef.current = 0;
        }, 5000);
      });
    },
    [fireAiPrompt, language, questionId, questionTitle, registerGhostText]
  );

  useEffect(() => {
    if (monacoRef.current) {
      registerGhostText(monacoRef.current, language);
    }
  }, [language, registerGhostText]);

  const pollJudgeResult = useCallback(
    async (requestId: string) => {
      for (let attempt = 0; attempt < 6; attempt += 1) {
        const response = await fetch(
          appApiPath(
            `/judge/result?questionId=${encodeURIComponent(questionId)}&requestId=${encodeURIComponent(requestId)}${
              examId ? `&examId=${encodeURIComponent(examId)}` : ""
            }`
          ),
          { cache: "no-store" }
        );

        if (response.ok) {
          const payload = (await response.json()) as Omit<JudgeResultDetail, "questionId">;
          if (payload.status !== "Pending") {
            return payload;
          }
        }

        await sleep(1500);
      }

      return null;
    },
    [examId, questionId]
  );

  const handleRun = useCallback(async () => {
    clearEditorErrors();
    setRunResult(null);
    setShowConsole(true);

    if (frontendPreviewMode) {
      setJudgeStage({ label: "当前是前端预览模式，运行代码功能已禁用。", done: true, error: false });
      setRunResult({
        runStatus: "PREVIEW",
        exeMessage: "这里只保留编辑器与结果面板的界面预览，不会真正调用后端运行代码。",
        useMemory: null,
        useTime: null,
        caseResults: []
      });
      window.setTimeout(() => setJudgeStage(null), 2200);
      return;
    }

    if (!questionId || !Number.isFinite(Number(questionId))) {
      setJudgeStage({ label: "当前题目没有可运行的后端 questionId。", done: true, error: true });
      return;
    }

    if (!isJudgeLanguageSupported(language)) {
      setJudgeStage({ label: "当前真实运行仅支持 Java。", done: true, error: true });
      return;
    }

    const token = getBrowserAccessToken();
    if (!token) {
      setJudgeStage({ label: "未登录，无法运行真实代码。", done: true, error: true });
      return;
    }

    setJudgeStage({ label: "正在运行代码..." });

    try {
      const response = await fetch(appApiPath("/judge/run"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          questionId,
          examId,
          language,
          code: activeCode,
          customInputs: parseCustomInputs(customInput)
        })
      });

      const payload = (await response.json()) as RunResult & { message?: string };
      if (!response.ok) {
        throw new Error(payload.message ?? "运行代码失败。");
      }

      setRunResult(payload);
      const failedSample = payload.caseResults?.some((item) => item.custom !== true && item.passed === false);
      setJudgeStage({
        label: failedSample ? "运行完成，样例中存在未通过用例。" : "运行完成，结果已同步到下方面板。",
        done: true,
        error: Boolean(failedSample)
      });
      window.setTimeout(() => setJudgeStage(null), 2200);
    } catch (error) {
      const message = error instanceof Error ? error.message : "运行代码失败。";
      setJudgeStage({ label: message, done: true, error: true });
      window.setTimeout(() => setJudgeStage(null), 2200);
    }
  }, [activeCode, clearEditorErrors, customInput, examId, language, questionId]);

  const handleSubmit = useCallback(async () => {
    clearEditorErrors();

    if (frontendPreviewMode) {
      const message = "当前是前端预览模式，提交评测功能已禁用。";
      setJudgeStage({ label: message, done: true, error: false });
      emitJudgeResult({ questionId, status: "Pending", message });
      window.setTimeout(() => setJudgeStage(null), 2200);
      return;
    }

    if (!questionId || !Number.isFinite(Number(questionId))) {
      setJudgeStage({ label: "当前题目没有可提交的后端 questionId。", done: true, error: true });
      return;
    }

    if (!isJudgeLanguageSupported(language)) {
      const message = "当前真实判题仅支持 Java。";
      setJudgeStage({ label: message, done: true, error: true });
      emitJudgeResult({ questionId, status: "Compile Error", message });
      window.setTimeout(() => setJudgeStage(null), 2200);
      return;
    }

    const token = getBrowserAccessToken();
    if (!token) {
      setJudgeStage({ label: "未登录，无法提交判题。", done: true, error: true });
      return;
    }

    wsRef.current?.close();
    setJudgeStage({ label: "提交判题任务中..." });

    try {
      const response = await fetch(appApiPath("/judge/submit"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          questionId,
          examId,
          language,
          code: activeCode
        })
      });

      const payload = (await response.json()) as { requestId?: string; status?: string; message?: string };
      if (!response.ok || !payload.requestId) {
        throw new Error(payload.message ?? "提交判题失败。");
      }

      const requestId = payload.requestId;
        emitJudgeSubmitted({
          questionId,
          examId,
          requestId,
          language: languageLabels[language]
        });

      setJudgeStage({ label: "判题任务已接收，正在建立实时订阅..." });

      const socket = new WebSocket(
        `${resolveJudgeWebSocketUrl()}?token=${encodeURIComponent(token.startsWith("Bearer ") ? token : `Bearer ${token}`)}`
      );
      wsRef.current = socket;

      let finalized = false;

      const finalize = (detail: Omit<JudgeResultDetail, "questionId">) => {
        if (finalized) return;
        finalized = true;

        if (detail.failLine) {
          setEditorError(detail.failLine, detail.message ?? "该行附近存在错误。");
        }

        emitJudgeResult({ questionId, ...detail });
        setJudgeStage({
          label: `判题完成 · ${detail.status}`,
          done: true,
          error: detail.status !== "Accepted"
        });

        window.setTimeout(() => setJudgeStage(null), 2200);
        socket.close();
        if (wsRef.current === socket) wsRef.current = null;
      };

      socket.onopen = () => {
        setJudgeStage({ label: "实时订阅已建立，等待判题结果..." });
        socket.send(JSON.stringify({ type: "subscribe", requestId }));
      };

      socket.onmessage = async (event) => {
        const data = JSON.parse(event.data) as JudgeSocketPayload;

        if (data.type === "error") {
          const message = data.message ?? "判题实时通道返回错误。";
          const fallback = await pollJudgeResult(requestId);
          if (fallback) {
            finalize(fallback);
            return;
          }

          finalize({
            requestId,
            status: "Compile Error",
            message
          });
          return;
        }

        const outcome = normalizeJudgeOutcome(data);
        if (outcome.status === "Pending") {
          setJudgeStage({ label: "后端已接收任务，正在判题..." });
          return;
        }

        finalize(outcome);
      };

      socket.onerror = async () => {
        setJudgeStage({ label: "实时通道异常，正在补拉判题结果..." });
        const fallback = await pollJudgeResult(requestId);
        if (fallback) {
          finalize(fallback);
          return;
        }

        finalize({
          requestId,
          status: "Pending",
          message: "实时通道异常，请在提交记录中查看最终结果。"
        });
      };

      socket.onclose = async () => {
        if (finalized) return;
        const fallback = await pollJudgeResult(requestId);
        if (fallback) {
          finalize(fallback);
        }
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "提交判题失败。";
      setJudgeStage({ label: message, done: true, error: true });
      emitJudgeResult({ questionId, status: "Compile Error", message });
      window.setTimeout(() => setJudgeStage(null), 2200);
    }
  }, [activeCode, clearEditorErrors, examId, language, pollJudgeResult, questionId, setEditorError]);

  const submitEnabled = isJudgeLanguageSupported(language);

  return (
    <div className="flex h-full flex-col bg-[var(--surface-1)]">
      <div className="flex items-center justify-between border-b border-[var(--border-soft)] bg-[var(--surface-1)] px-4 pt-3">
        <div className="space-y-0.5 pb-4">
          <p className="kicker">Editor</p>
          <h3 className="text-base font-semibold text-[var(--text-primary)]">代码编辑区</h3>
        </div>

        <div className="lang-tabs-bar pb-0">
          {availableLanguages.map((item) => (
            <button
              key={item}
              data-active={item === language ? "true" : "false"}
              className="lang-tab"
              onClick={() => {
                startTransition(() => setLanguage(item));
              }}
              type="button"
            >
              {languageLabels[item]}
            </button>
          ))}
        </div>
      </div>

      <div className="code-editor-frame flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-2">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
            <span className="text-xs text-[var(--text-secondary)]">Monaco 已启用多语言高亮</span>
          </div>
          <span className="text-xs text-[var(--text-muted)]">{submitEnabled ? "当前真实运行与判题支持 Java" : "当前语言仅支持编辑与 AI 辅助"}</span>
        </div>

        {!mounted ? (
          <pre className="m-0 flex-1 overflow-auto bg-[var(--surface-1)] p-5 text-sm leading-7 text-[var(--text-secondary)]">{activeCode}</pre>
        ) : (
          <MonacoEditor
            height="100%"
            language={monacoLanguages[language]}
            loading={<pre className="m-0 flex-1 overflow-auto bg-[var(--surface-1)] p-5 text-sm leading-7 text-[var(--text-secondary)]">{activeCode}</pre>}
            options={{
              fontFamily: "JetBrains Mono, IBM Plex Mono, monospace",
              fontSize: 13,
              lineHeight: 22,
              minimap: { enabled: false },
              padding: { top: 16, bottom: 16 },
              scrollbar: { verticalScrollbarSize: 6 },
              smoothScrolling: true,
              renderLineHighlight: "line",
              inlineSuggest: { enabled: true },
              quickSuggestions: false
            }}
            theme={lightTheme ? "vs" : "vs-dark"}
            value={activeCode}
            onMount={handleEditorMount}
            onChange={(value) => {
              setDrafts((current) => ({
                ...current,
                [language]: value ?? ""
              }));
            }}
          />
        )}
      </div>

      <div className="flex flex-col border-t border-[var(--border-soft)] bg-[var(--surface-1)]">
        {judgeStage ? (
          <div className="border-b border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
            <div className="flex items-center gap-3">
              {judgeStage.done ? (
                <CheckCircle2
                  size={14}
                  className={judgeStage.error ? "shrink-0 text-[var(--danger)]" : "shrink-0 text-[var(--success)]"}
                />
              ) : (
                <Loader2 size={14} className="shrink-0 animate-spin text-[var(--accent)]" />
              )}
              <div className="flex-1 space-y-1.5">
                <p className="text-xs font-medium text-[var(--text-primary)]">{judgeStage.label}</p>
                {!judgeStage.done ? (
                  <div className="h-1 w-full overflow-hidden rounded-full bg-[var(--surface-1)]">
                    <div className="h-full w-2/3 animate-pulse rounded-full bg-[var(--accent)]" />
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}

        {showConsole ? (
          <div className="border-b border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
            <div className="grid gap-4 xl:grid-cols-[0.92fr_1.08fr]">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-[var(--text-primary)]">公开样例</p>
                  <Tag tone="accent">{examples.length} 条</Tag>
                </div>
                <div className="space-y-3">
                  {examples.map((item, index) => (
                    <div key={`${item.input}-${index}`} className="rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] p-3">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">Input</p>
                      <pre className="mt-2 whitespace-pre-wrap font-mono text-xs leading-6 text-[var(--text-primary)]">{item.input}</pre>
                      <p className="mt-3 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">Expected</p>
                      <pre className="mt-2 whitespace-pre-wrap font-mono text-xs leading-6 text-[var(--text-primary)]">{item.output}</pre>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-xs font-semibold text-[var(--text-primary)]">自定义输入</p>
                <Textarea
                  value={customInput}
                  onChange={(event) => setCustomInput(event.target.value)}
                  placeholder={`每个输入块用 --- 分隔，例如：\n[2,7,11,15]\n9\n---\n[3,2,4]\n6`}
                  className="min-h-[120px] border-[var(--border-soft)] bg-[var(--surface-2)] font-mono text-[13px]"
                />
                <p className="text-xs leading-5 text-[var(--text-muted)]">运行代码会自动带上数据库中的公开样例，并把你的自定义输入一起送到后端执行。</p>
              </div>
            </div>

            {runResult ? (
              <div className="mt-4 rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Tag tone={runResult.runStatus === "SUCCEED" ? "success" : "warning"}>{runResult.runStatus ?? "UNKNOWN"}</Tag>
                  <span className="text-xs text-[var(--text-muted)]">时间 {runResult.useTime ?? "--"} ms</span>
                  <span className="text-xs text-[var(--text-muted)]">内存 {runResult.useMemory ?? "--"} KB</span>
                </div>
                {runResult.exeMessage ? (
                  <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">{runResult.exeMessage}</p>
                ) : null}
                <div className="mt-4 space-y-3">
                  {runResult.caseResults?.map((item, index) => (
                    <div key={`${item.input}-${index}`} className="rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-1)] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold text-[var(--text-primary)]">Case {index + 1}</p>
                        <Tag tone={item.custom ? "default" : item.passed ? "success" : "warning"}>
                          {item.custom ? "自定义" : item.passed ? "通过" : "未通过"}
                        </Tag>
                      </div>
                      <p className="mt-3 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">Input</p>
                      <pre className="mt-2 whitespace-pre-wrap font-mono text-xs leading-6 text-[var(--text-primary)]">{item.input}</pre>
                      {!item.custom ? (
                        <>
                          <p className="mt-3 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">Expected</p>
                          <pre className="mt-2 whitespace-pre-wrap font-mono text-xs leading-6 text-[var(--text-primary)]">{item.expectedOutput}</pre>
                        </>
                      ) : null}
                      <p className="mt-3 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">Actual</p>
                      <pre className="mt-2 whitespace-pre-wrap font-mono text-xs leading-6 text-[var(--text-primary)]">{item.actualOutput}</pre>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => setShowConsole((current) => !current)}
            className="flex items-center gap-1.5 text-[13px] font-medium text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
          >
            <Terminal size={13} />
            <span className="ml-1">{showConsole ? "收起测试台" : "测试用例"}</span>
          </button>

          <div className="flex items-center gap-3">
            <Button variant="secondary" size="sm" id="btn-run-code" className="h-8 px-4 font-medium" onClick={handleRun}>
              <Play size={13} className="mr-1.5 text-[var(--text-secondary)]" />
              {frontendPreviewMode ? "预览运行区" : "运行代码"}
            </Button>
            <Button
              size="sm"
              id="btn-submit-code"
              className="h-8 px-5 font-semibold"
              onClick={handleSubmit}
              disabled={!submitEnabled && !frontendPreviewMode}
            >
              <SendHorizontal size={13} className="mr-1.5 opacity-90" />
              {frontendPreviewMode ? "预览提交区" : "提交评测"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
