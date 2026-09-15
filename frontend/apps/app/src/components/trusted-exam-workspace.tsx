"use client";

import * as React from "react";
import {
  AlertTriangle, Check, CheckCircle2, Clock3, Cloud, CloudOff, FileCode2,
  LoaderCircle, LockKeyhole, Play, RefreshCw, Send, ShieldCheck
} from "lucide-react";
import { Button, Panel, Tag } from "@aioj/ui";

import { createDemoExamAccess, createDemoExamAttempt, type DemoExamLifecycle } from "./demo-trusted-exam";
import { appApiPath } from "../lib/paths";

export type Access = {
  title: string;
  description?: string;
  serverNow: string;
  startAt: string;
  latestStartAt: string;
  durationMinutes: number;
  privacyNotice: string;
  canStart: boolean;
  canResume: boolean;
};

export type Question = {
  versionQuestionId: string;
  questionOrder: number;
  score: number;
  required: boolean;
  title: string;
  content: string;
  timeLimit: number;
  spaceLimit: number;
  allowedLanguages: string[];
  starterCode: Record<string, string>;
};

export type Answer = {
  answerId?: string;
  versionQuestionId: string;
  language: string;
  content: string;
  answerVersion: number;
  savedAt?: string;
  frozen: boolean;
};

export type Attempt = {
  attemptId: string;
  title: string;
  description?: string;
  status: string;
  serverNow: string;
  deadlineAt: string;
  submittedAt?: string;
  questions: Question[];
  answers: Answer[];
};

type ExamResult = {
  totalScore: number;
  maxScore: number;
  releasedAt: string;
  items: Array<{ versionQuestionId: string; awardedScore: number; maxScore: number }>;
};

type SaveState = "idle" | "dirty" | "saving" | "saved" | "offline" | "conflict";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const response = await fetch(appApiPath(`/trusted-exams/${path}`), { ...init, headers });
  const payload = (await response.json().catch(() => null)) as T | { message?: string } | null;
  if (!response.ok) {
    throw new Error((payload as { message?: string } | null)?.message ?? "请求失败，请稍后重试。");
  }
  return payload as T;
}

function idempotencyKey(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`;
}

function getSessionId(examId: string) {
  const key = `syncode-exam-session:${examId}`;
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;
  const created = crypto.randomUUID();
  window.localStorage.setItem(key, created);
  return created;
}

function nextIntegritySequence(attemptId: string) {
  const key = `syncode-integrity-sequence:${attemptId}`;
  const next = Number(window.localStorage.getItem(key) ?? "0") + 1;
  window.localStorage.setItem(key, String(next));
  return next;
}

function formatRemaining(milliseconds: number) {
  const value = Math.max(0, Math.floor(milliseconds / 1000));
  return [Math.floor(value / 3600), Math.floor((value % 3600) / 60), value % 60]
    .map((item) => String(item).padStart(2, "0"))
    .join(":");
}

function formatDateTime(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  }).format(date);
}

function demoStateKey(examId: string) {
  return `syncode-demo-exam-state:${examId}`;
}

function readDemoLifecycle(examId: string): DemoExamLifecycle | null {
  try {
    const stored = window.localStorage.getItem(demoStateKey(examId));
    if (!stored) return null;
    const state = JSON.parse(stored) as DemoExamLifecycle;
    return state.status === "IN_PROGRESS" || state.status === "SUBMITTED" ? state : null;
  } catch {
    return null;
  }
}

export function TrustedExamWorkspace({ examId, demoMode = false }: { examId: string; demoMode?: boolean }) {
  const [access, setAccess] = React.useState<Access | null>(null);
  const [attempt, setAttempt] = React.useState<Attempt | null>(null);
  const [result, setResult] = React.useState<ExamResult | null>(null);
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [drafts, setDrafts] = React.useState<Record<string, Answer>>({});
  const [saveState, setSaveState] = React.useState<SaveState>("idle");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [remaining, setRemaining] = React.useState(0);
  const clockOffset = React.useRef(0);
  const integrityQueue = React.useRef<Array<Record<string, unknown>>>([]);
  const draftsRef = React.useRef<Record<string, Answer>>({});

  const terminal = Boolean(attempt && attempt.status !== "IN_PROGRESS");
  const activeQuestion = attempt?.questions.find((item) => item.versionQuestionId === activeId)
    ?? attempt?.questions[0];
  const activeAnswer = activeQuestion ? drafts[activeQuestion.versionQuestionId] : undefined;

  const loadResult = React.useCallback(async (attemptId: string) => {
    if (demoMode) {
      setResult(null);
      return;
    }
    try {
      setResult(await api<ExamResult>(`attempts/${attemptId}/result`));
    } catch {
      setResult(null);
    }
  }, [demoMode]);

  const applyAttempt = React.useCallback((next: Attempt) => {
    setAttempt(next);
    setActiveId((current) => current ?? next.questions[0]?.versionQuestionId ?? null);
    const restored: Record<string, Answer> = {};
    next.questions.forEach((question) => {
      const serverAnswer = next.answers.find((answer) => answer.versionQuestionId === question.versionQuestionId);
      const local = window.localStorage.getItem(`syncode-exam-draft:${next.attemptId}:${question.versionQuestionId}`);
      const base = serverAnswer ?? {
        versionQuestionId: question.versionQuestionId,
        language: question.allowedLanguages[0] ?? "java",
        content: question.starterCode.java ?? "",
        answerVersion: 0,
        frozen: false
      };
      restored[question.versionQuestionId] = local === null ? base : { ...base, content: local };
    });
    draftsRef.current = restored;
    setDrafts(restored);
    clockOffset.current = new Date(next.serverNow).getTime() - Date.now();
    setRemaining(new Date(next.deadlineAt).getTime() - (Date.now() + clockOffset.current));
    if (next.status !== "IN_PROGRESS") void loadResult(next.attemptId);
  }, [loadResult]);

  const loadAccess = React.useCallback(async () => {
    setError(null);
    try {
      if (demoMode) {
        const lifecycle = readDemoLifecycle(examId);
        setAccess(createDemoExamAccess(examId, lifecycle?.status === "IN_PROGRESS"));
        if (lifecycle) applyAttempt(createDemoExamAttempt(examId, lifecycle));
        return;
      }
      const next = await api<Access>(`exams/${examId}/access`);
      setAccess(next);
      clockOffset.current = new Date(next.serverNow).getTime() - Date.now();
      if (next.canResume) applyAttempt(await api<Attempt>(`exams/${examId}/attempts/current`));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "无法检查考试资格。");
    }
  }, [applyAttempt, demoMode, examId]);

  React.useEffect(() => { void loadAccess(); }, [loadAccess]);

  React.useEffect(() => {
    if (!attempt || terminal) return;
    const timer = window.setInterval(() => {
      const next = new Date(attempt.deadlineAt).getTime() - (Date.now() + clockOffset.current);
      setRemaining(next);
      if (next <= 0) {
        if (demoMode) {
          const submittedAt = new Date().toISOString();
          const lifecycle: DemoExamLifecycle = {
            status: "SUBMITTED",
            serverNow: submittedAt,
            deadlineAt: attempt.deadlineAt,
            submittedAt
          };
          window.localStorage.setItem(demoStateKey(examId), JSON.stringify(lifecycle));
          applyAttempt({ ...attempt, status: "SUBMITTED", submittedAt });
        } else {
          void api<Attempt>(`exams/${examId}/attempts/current`).then(applyAttempt).catch(() => undefined);
        }
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [applyAttempt, attempt, demoMode, examId, terminal]);

  const flushIntegrity = React.useCallback(async () => {
    if (demoMode || !attempt || terminal || integrityQueue.current.length === 0) return;
    const events = integrityQueue.current.splice(0);
    try {
      await api(`attempts/${attempt.attemptId}/integrity-events`, {
        method: "POST",
        body: JSON.stringify({ sessionId: getSessionId(examId), events })
      });
    } catch {
      integrityQueue.current.unshift(...events);
    }
  }, [attempt, demoMode, examId, terminal]);

  React.useEffect(() => {
    if (demoMode || !attempt || terminal) return;
    const record = (eventType: string, metadata: Record<string, unknown> = {}) => integrityQueue.current.push({
      clientSequence: nextIntegritySequence(attempt.attemptId),
      eventType,
      clientObservedTime: new Date().toISOString(),
      metadata
    });
    const visibility = () => document.hidden && record("FOCUS_LOST", { visibilityState: document.visibilityState });
    const fullscreen = () => !document.fullscreenElement && record("FULLSCREEN_EXIT", { fullscreen: false });
    const paste = (event: ClipboardEvent) => record("PASTE", { target: (event.target as HTMLElement | null)?.tagName ?? "unknown" });
    const copy = (event: ClipboardEvent) => record("COPY", { target: (event.target as HTMLElement | null)?.tagName ?? "unknown" });
    document.addEventListener("visibilitychange", visibility);
    document.addEventListener("fullscreenchange", fullscreen);
    document.addEventListener("paste", paste);
    document.addEventListener("copy", copy);
    const timer = window.setInterval(() => void flushIntegrity(), 15000);
    return () => {
      document.removeEventListener("visibilitychange", visibility);
      document.removeEventListener("fullscreenchange", fullscreen);
      document.removeEventListener("paste", paste);
      document.removeEventListener("copy", copy);
      window.clearInterval(timer);
    };
  }, [attempt, demoMode, flushIntegrity, terminal]);

  React.useEffect(() => {
    if (demoMode || !attempt || terminal) return;
    const timer = window.setInterval(async () => {
      try {
        const heartbeat = await api<{ serverNow: string; status: string }>(`attempts/${attempt.attemptId}/heartbeat`, {
          method: "POST",
          body: JSON.stringify({ sessionId: getSessionId(examId), takeover: true })
        });
        clockOffset.current = new Date(heartbeat.serverNow).getTime() - Date.now();
        if (heartbeat.status !== "IN_PROGRESS") {
          applyAttempt(await api<Attempt>(`exams/${examId}/attempts/current`));
        }
      } catch {
        setSaveState("offline");
      }
    }, 20000);
    return () => window.clearInterval(timer);
  }, [applyAttempt, attempt, demoMode, examId, terminal]);

  const persistAnswer = React.useCallback(async (attemptId: string, questionId: string, answer: Answer) => {
      const saved = demoMode
        ? { ...answer, answerVersion: answer.answerVersion + 1, savedAt: new Date().toISOString() }
        : await api<Answer>(`attempts/${attemptId}/answers/${questionId}`, {
            method: "PUT",
            body: JSON.stringify({
              answerType: "CODE",
              language: answer.language,
              content: answer.content,
              expectedVersion: answer.answerVersion
            })
          });
      const latest = draftsRef.current[questionId];
      const unchanged = latest?.content === answer.content && latest?.language === answer.language;
      const next = unchanged ? saved : {
        ...latest,
        answerId: saved.answerId,
        answerVersion: saved.answerVersion,
        savedAt: saved.savedAt
      };
      draftsRef.current = { ...draftsRef.current, [questionId]: next };
      setDrafts(draftsRef.current);
      if (unchanged) {
        if (!demoMode) window.localStorage.removeItem(`syncode-exam-draft:${attemptId}:${questionId}`);
        setSaveState("saved");
      } else {
        setSaveState("dirty");
      }
      return saved;
  }, [demoMode]);

  const saveActive = React.useCallback(async () => {
    if (!attempt || !activeQuestion || !activeAnswer || terminal) return activeAnswer;
    setSaveState("saving");
    try {
      return await persistAnswer(attempt.attemptId, activeQuestion.versionQuestionId, activeAnswer);
    } catch (nextError) {
      setSaveState(nextError instanceof Error && nextError.message.includes("版本") ? "conflict" : "offline");
      setError(nextError instanceof Error ? nextError.message : "自动保存失败。");
      throw nextError;
    }
  }, [activeAnswer, activeQuestion, attempt, persistAnswer, terminal]);

  React.useEffect(() => {
    if (saveState !== "dirty") return;
    const timer = window.setTimeout(() => void saveActive().catch(() => undefined), 1200);
    return () => window.clearTimeout(timer);
  }, [saveActive, saveState]);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      if (demoMode) {
        const next = createDemoExamAttempt(examId);
        const lifecycle: DemoExamLifecycle = {
          status: "IN_PROGRESS",
          serverNow: next.serverNow,
          deadlineAt: next.deadlineAt
        };
        window.localStorage.setItem(demoStateKey(examId), JSON.stringify(lifecycle));
        setAccess(createDemoExamAccess(examId, true));
        applyAttempt(next);
        return;
      }
      applyAttempt(await api<Attempt>(`exams/${examId}/attempts/start`, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey("start") },
        body: JSON.stringify({ sessionId: getSessionId(examId) })
      }));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "开始考试失败。");
    } finally {
      setBusy(false);
    }
  }

  function updateCode(content: string) {
    if (!attempt || !activeQuestion || !activeAnswer) return;
    draftsRef.current = {
      ...draftsRef.current,
      [activeQuestion.versionQuestionId]: { ...activeAnswer, content }
    };
    setDrafts(draftsRef.current);
    window.localStorage.setItem(`syncode-exam-draft:${attempt.attemptId}:${activeQuestion.versionQuestionId}`, content);
    setSaveState("dirty");
  }

  async function submit(kind: "RUN" | "FORMAL") {
    setBusy(true);
    setError(null);
    try {
      const saved = await saveActive();
      if (!attempt || !activeQuestion || !saved) return;
      if (demoMode) {
        setNotice(kind === "RUN"
          ? "体验运行已完成：这里不会调用真实判题服务。"
          : "体验提交已记录在当前浏览器，不会生成真实成绩。");
        return;
      }
      const response = await api<{ remainingFormalSubmissions: number }>(`attempts/${attempt.attemptId}/submissions`, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey("judge") },
        body: JSON.stringify({
          versionQuestionId: activeQuestion.versionQuestionId,
          answerVersion: saved.answerVersion,
          submitKind: kind
        })
      });
      setNotice(kind === "RUN" ? "运行请求已提交。" : `正式提交已接收，还可提交 ${response.remainingFormalSubmissions} 次。`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "提交失败。");
    } finally {
      setBusy(false);
    }
  }

  async function finalize() {
    if (!attempt || !window.confirm("交卷后答案将被冻结，确定交卷吗？")) return;
    setBusy(true);
    setError(null);
    try {
      if (demoMode) {
        const submittedAt = new Date().toISOString();
        const lifecycle: DemoExamLifecycle = {
          status: "SUBMITTED",
          serverNow: submittedAt,
          deadlineAt: attempt.deadlineAt,
          submittedAt
        };
        window.localStorage.setItem(demoStateKey(examId), JSON.stringify(lifecycle));
        applyAttempt({
          ...attempt,
          status: "SUBMITTED",
          serverNow: submittedAt,
          submittedAt,
          answers: Object.values(draftsRef.current).map((answer) => ({ ...answer, frozen: true }))
        });
        return;
      }
      for (const question of attempt.questions) {
        const key = `syncode-exam-draft:${attempt.attemptId}:${question.versionQuestionId}`;
        const answer = draftsRef.current[question.versionQuestionId];
        if (answer && window.localStorage.getItem(key) !== null) {
          await persistAnswer(attempt.attemptId, question.versionQuestionId, answer);
        }
      }
      await flushIntegrity();
      await api(`attempts/${attempt.attemptId}/finalize`, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey("finalize") },
        body: "{}"
      });
      applyAttempt(await api<Attempt>(`exams/${examId}/attempts/current`));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "交卷失败，请重试。");
    } finally {
      setBusy(false);
    }
  }

  function resetDemo() {
    if (!attempt) return;
    window.localStorage.removeItem(demoStateKey(examId));
    attempt.questions.forEach((question) => {
      window.localStorage.removeItem(`syncode-exam-draft:${attempt.attemptId}:${question.versionQuestionId}`);
    });
    draftsRef.current = {};
    setDrafts({});
    setAttempt(null);
    setResult(null);
    setNotice(null);
    setError(null);
    setSaveState("idle");
    setAccess(createDemoExamAccess(examId));
  }

  if (!access && !error) {
    return <div className="flex min-h-[60vh] items-center justify-center"><LoaderCircle className="animate-spin text-[var(--text-muted)]" /></div>;
  }

  if (!attempt) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10 md:px-6">
        <Panel tone="strong" className="p-6 md:p-8">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[8px] bg-[var(--surface-3)]"><ShieldCheck size={21} /></div>
            <div className="min-w-0"><p className="kicker">考试进入检查</p><h1 className="mt-2 text-3xl font-semibold">{access?.title ?? "无法进入考试"}</h1><p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">{access?.description}</p></div>
          </div>
          {access ? <div className="mt-7 grid gap-3 md:grid-cols-3">
            <div className="border-t border-[var(--border-soft)] pt-4"><p className="text-xs text-[var(--text-muted)]">开始时间</p><p className="mt-2 text-sm">{demoMode ? "现在可进入" : formatDateTime(access.startAt)}</p></div>
            <div className="border-t border-[var(--border-soft)] pt-4"><p className="text-xs text-[var(--text-muted)]">最晚入场</p><p className="mt-2 text-sm">{demoMode ? "今日体验时段内" : formatDateTime(access.latestStartAt)}</p></div>
            <div className="border-t border-[var(--border-soft)] pt-4"><p className="text-xs text-[var(--text-muted)]">作答时长</p><p className="mt-2 text-sm">{access.durationMinutes} 分钟</p></div>
          </div> : null}
          <div className="mt-7 border-l-2 border-[var(--warning)] pl-4 text-sm leading-7 text-[var(--text-secondary)]">{access?.privacyNotice}</div>
          {error ? <p className="mt-5 flex items-center gap-2 text-sm text-[var(--danger)]"><AlertTriangle size={15} />{error}</p> : null}
          <div className="mt-7 flex gap-3"><Button onClick={() => void start()} disabled={!access?.canStart || busy}>{busy ? <LoaderCircle size={15} className="animate-spin" /> : <Play size={15} />}{demoMode ? "进入体验考试" : "开始考试"}</Button><Button variant="secondary" onClick={() => void loadAccess()}><RefreshCw size={15} />重新检查</Button></div>
        </Panel>
      </div>
    );
  }

  return <div className="grid h-full min-h-0 grid-rows-[auto_1fr] bg-[var(--bg)]">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3 md:px-6">
      <div className="min-w-0"><div className="flex items-center gap-2"><p className="truncate text-sm font-semibold">{attempt.title}</p>{demoMode ? <Tag>体验卷</Tag> : null}</div><p className="mt-1 text-xs text-[var(--text-muted)]">{demoMode ? "本地体验计时" : "服务端计时"} · {attempt.questions.length} 题 · 100 分</p></div>
      <div className="flex items-center gap-2"><div className="flex h-9 items-center gap-2 rounded-[8px] border border-[var(--border-soft)] bg-[var(--surface-3)] px-3 font-mono text-sm"><Clock3 size={15} />{formatRemaining(remaining)}</div><Button size="sm" variant="secondary" onClick={() => void finalize()} disabled={busy || terminal}><Send size={14} />交卷</Button></div>
    </header>
    {terminal ? <div className="flex items-center justify-center overflow-auto p-6"><Panel className="w-full max-w-xl p-8 text-center"><CheckCircle2 size={36} className="mx-auto text-[var(--success)]" /><h1 className="mt-4 text-2xl font-semibold">交卷已确认</h1><p className="mt-3 text-sm text-[var(--text-secondary)]">{formatDateTime(attempt.submittedAt)}</p>{demoMode ? <div className="mt-5"><p className="text-sm leading-7 text-[var(--text-muted)]">体验流程已经完成。本次作答只保存在当前浏览器，没有执行真实判题，也不会计入成绩。</p><Button className="mt-4" size="sm" variant="secondary" onClick={resetDemo}><RefreshCw size={14} />重新体验</Button></div> : result ? <div className="mt-6 border-t border-[var(--border-soft)] pt-6"><p className="text-sm text-[var(--text-muted)]">最终成绩</p><p className="mt-2 text-4xl font-semibold">{result.totalScore}<span className="text-lg text-[var(--text-muted)]"> / {result.maxScore}</span></p></div> : <div className="mt-5"><p className="text-sm text-[var(--text-muted)]">成绩将在教师发布后显示。</p><Button className="mt-4" size="sm" variant="secondary" onClick={() => void loadResult(attempt.attemptId)}><RefreshCw size={14} />刷新成绩</Button></div>}</Panel></div> :
      <div className="grid min-h-0 overflow-auto lg:grid-cols-[220px_minmax(0,0.85fr)_minmax(420px,1.15fr)] lg:overflow-hidden">
        <aside className="border-b border-[var(--border-soft)] bg-[var(--surface-2)] p-3 lg:overflow-auto lg:border-b-0 lg:border-r"><p className="px-2 py-2 text-xs font-semibold text-[var(--text-muted)]">题目导航</p><div className="flex gap-1 overflow-x-auto lg:block lg:space-y-1">{attempt.questions.map((question) => { const answer = drafts[question.versionQuestionId]; const selected = question.versionQuestionId === activeQuestion?.versionQuestionId; return <button key={question.versionQuestionId} aria-current={selected ? "step" : undefined} onClick={() => setActiveId(question.versionQuestionId)} className={`flex min-w-[190px] items-center gap-3 rounded-[8px] px-3 py-3 text-left text-sm lg:w-full lg:min-w-0 ${selected ? "bg-[var(--surface-1)]" : "text-[var(--text-secondary)] hover:bg-[var(--surface-3)]"}`}><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--border-soft)] font-mono text-xs">{answer?.answerVersion > 0 ? <Check size={13} /> : question.questionOrder}</span><span className="min-w-0 flex-1 truncate">{question.title}</span><span className="text-xs text-[var(--text-muted)]">{question.score}</span></button>; })}</div></aside>
        <main className="border-b border-[var(--border-soft)] p-5 md:p-6 lg:overflow-auto lg:border-b-0 lg:border-r"><div className="flex flex-wrap gap-2"><Tag tone="accent">第 {activeQuestion?.questionOrder} 题</Tag><Tag>{activeQuestion?.score} 分</Tag>{activeQuestion?.required ? <Tag tone="warning">必答</Tag> : null}</div><h1 className="mt-4 text-2xl font-semibold">{activeQuestion?.title}</h1><div className="mt-6 whitespace-pre-wrap text-sm leading-8 text-[var(--text-secondary)]">{activeQuestion?.content}</div><div className="mt-8 flex gap-4 border-t border-[var(--border-soft)] pt-4 text-xs text-[var(--text-muted)]"><span>时间 {activeQuestion?.timeLimit} ms</span><span>内存 {activeQuestion?.spaceLimit} KB</span></div></main>
        <section className="grid min-h-[520px] grid-rows-[auto_1fr_auto] bg-[var(--surface-1)] lg:min-h-0"><div className="flex items-center justify-between border-b border-[var(--border-soft)] px-4 py-3"><div className="flex items-center gap-2 text-sm font-medium"><FileCode2 size={15} />Java</div><div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">{saveState === "saving" ? <LoaderCircle size={13} className="animate-spin" /> : saveState === "offline" || saveState === "conflict" ? <CloudOff size={13} /> : <Cloud size={13} />}{saveState === "dirty" ? "待保存" : saveState === "saving" ? "保存中" : saveState === "offline" ? "网络异常" : saveState === "conflict" ? "版本冲突" : demoMode ? "已保存到本机" : "已保存"}</div></div><textarea aria-label="代码编辑器" spellCheck={false} readOnly={busy} value={activeAnswer?.content ?? ""} onChange={(event) => updateCode(event.target.value)} className="min-h-[360px] w-full resize-none bg-[#101418] p-5 font-mono text-sm leading-7 text-[#e8edf2] outline-none" /><div className="border-t border-[var(--border-soft)] p-4">{error ? <p className="mb-3 flex items-center gap-2 text-sm text-[var(--danger)]"><AlertTriangle size={14} />{error}</p> : null}{notice ? <p className="mb-3 text-sm text-[var(--success)]">{notice}</p> : null}<div className="flex flex-wrap justify-between gap-3"><div className="flex items-center gap-2 text-xs text-[var(--text-muted)]"><LockKeyhole size={13} />{demoMode ? "体验操作不会发送到判题服务" : "正式提交使用当前已保存版本"}</div><div className="flex gap-2"><Button size="sm" variant="secondary" disabled={busy} onClick={() => void submit("RUN")}><Play size={14} />运行</Button><Button size="sm" disabled={busy} onClick={() => void submit("FORMAL")}><Send size={14} />提交</Button></div></div></div></section>
      </div>}
  </div>;
}
