"use client";

import * as React from "react";
import { AlertTriangle, Ban, ClipboardCheck, RefreshCw, Send, ShieldCheck, UserPlus, Users } from "lucide-react";
import { Button, Input, Panel, Tag } from "@aioj/ui";

import { frontendPreviewMode } from "@aioj/config";
import { adminApiPath } from "../lib/paths";

type Candidate = {
  userId: string;
  attemptId?: string;
  nickName?: string;
  email?: string;
  authorized: boolean;
  attemptStatus?: string;
  lastActiveAt?: string;
  riskLevel?: number;
};

type Monitor = {
  status: string;
  serverNow: string;
  authorized: number;
  notStarted: number;
  inProgress: number;
  disconnected: number;
  submitted: number;
  timedOut: number;
  cancelled: number;
  candidates: Candidate[];
};

type Grade = {
  gradeId: string;
  attemptId: string;
  userId: string;
  nickName?: string;
  status: string;
  totalScore: number;
  maxScore: number;
  riskLevel?: number;
};

type Evidence = {
  category: string;
  eventType: string;
  serverTime: string;
  riskPoints: number;
  metadataJson?: string;
};

type GradeReview = {
  attemptId: string; candidateName: string; status: string; totalScore: number; maxScore: number;
  items: Array<{ versionQuestionId: string; questionOrder: number; title: string; questionType: string; answerContent?: string; gradingRubric?: string; awardedScore: number; maxScore: number; gradingMode: string; feedback?: string }>;
};

async function request<T>(path: string, init?: RequestInit) {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const response = await fetch(adminApiPath(`/trusted-exams/${path}`), { ...init, headers });
  const payload = (await response.json().catch(() => null)) as T | { message?: string } | null;
  if (!response.ok) throw new Error((payload as { message?: string } | null)?.message ?? "操作失败。");
  return payload as T;
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    IN_PROGRESS: "作答中", SUBMITTED: "已交卷", TIMED_OUT: "已超时", CANCELLED: "已取消",
    WAITING_FOR_JUDGE: "判题中", READY: "待发布", RELEASED: "已发布", NEEDS_REVIEW: "需复核"
  };
  return status ? labels[status] ?? status : "未开始";
}

export function AdminExamOperations({ examId }: { examId: string }) {
  const [monitor, setMonitor] = React.useState<Monitor | null>(null);
  const [grades, setGrades] = React.useState<Grade[]>([]);
  const [candidateIds, setCandidateIds] = React.useState("");
  const [evidence, setEvidence] = React.useState<Evidence[]>([]);
  const [selectedAttempt, setSelectedAttempt] = React.useState<string | null>(null);
  const [review, setReview] = React.useState<GradeReview | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    if (frontendPreviewMode) return;
    setError(null);
    try {
      const [nextMonitor, nextGrades] = await Promise.all([
        request<Monitor>(`${examId}/monitor`),
        request<Grade[]>(`${examId}/grades`)
      ]);
      setMonitor(nextMonitor);
      setGrades(nextGrades);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "考试运行数据加载失败。");
    }
  }, [examId]);

  React.useEffect(() => { void refresh(); }, [refresh]);

  async function authorize() {
    const userIds = candidateIds.split(/[,\s]+/).filter(Boolean).map(Number).filter(Number.isFinite);
    if (!userIds.length) return setError("请输入至少一个用户 ID。");
    setBusy(true);
    try {
      await request(`${examId}/candidates`, {
        method: "POST",
        body: JSON.stringify({ userIds, source: "MANUAL" })
      });
      setCandidateIds("");
      await refresh();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "授权失败。");
    } finally { setBusy(false); }
  }

  async function revoke(userId: string) {
    const reason = window.prompt("请输入撤销资格原因");
    if (!reason) return;
    setBusy(true);
    try {
      await request(`${examId}/candidates/${userId}`, { method: "DELETE", body: JSON.stringify({ reason }) });
      await refresh();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "撤销失败。");
    } finally { setBusy(false); }
  }

  async function cancelExam() {
    const reason = window.prompt("取消会终止所有进行中的作答，请输入原因");
    if (!reason) return;
    setBusy(true);
    try {
      await request(`${examId}/cancel`, { method: "POST", body: JSON.stringify({ reason }) });
      await refresh();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "取消考试失败。");
    } finally { setBusy(false); }
  }

  async function release() {
    if (!window.confirm("成绩发布后考生将立即可见，确定发布吗？")) return;
    setBusy(true);
    try {
      await request(`${examId}/results/release`, {
        method: "POST",
        headers: { "Idempotency-Key": `release-${crypto.randomUUID()}` },
        body: "{}"
      });
      await refresh();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "成绩发布失败。");
    } finally { setBusy(false); }
  }

  async function showEvidence(attemptId: string) {
    setEvidence([]);
    setSelectedAttempt(attemptId);
    try {
      const nextEvidence = await request<Evidence[] | null>(`${examId}/attempts/${attemptId}/evidence`);
      setEvidence(Array.isArray(nextEvidence) ? nextEvidence : []);
    }
    catch (nextError) { setError(nextError instanceof Error ? nextError.message : "证据加载失败。"); }
  }

  async function openReview(attemptId: string) {
    setError(null);
    try { setReview(await request<GradeReview>(`${examId}/attempts/${attemptId}/grading`)); }
    catch (nextError) { setError(nextError instanceof Error ? nextError.message : "阅卷详情加载失败。"); }
  }

  async function saveReview() {
    if (!review) return;
    setBusy(true); setError(null);
    try {
      const next = await request<GradeReview>(`${examId}/attempts/${review.attemptId}/grading`, {
        method: "PUT", headers: { "X-Request-ID": `review-${crypto.randomUUID()}` },
        body: JSON.stringify({ items: review.items.filter((item) => item.gradingMode === "MANUAL").map((item) => ({ versionQuestionId: item.versionQuestionId, awardedScore: Number(item.awardedScore), feedback: item.feedback })) })
      });
      setReview(next); await refresh();
    } catch (nextError) { setError(nextError instanceof Error ? nextError.message : "阅卷保存失败。"); }
    finally { setBusy(false); }
  }

  if (frontendPreviewMode) return null;

  const metrics = monitor ? [
    ["已授权", monitor.authorized], ["未开始", monitor.notStarted], ["作答中", monitor.inProgress],
    ["疑似断线", monitor.disconnected], ["已交卷", monitor.submitted], ["已超时", monitor.timedOut]
  ] : [];
  const canCancel = monitor ? ["PUBLISHED", "ACTIVE"].includes(monitor.status) : false;
  const canRelease = monitor?.status === "FINISHED" && grades.length > 0
    && grades.every((grade) => grade.status === "READY");

  return <div className="space-y-6">
    <Panel className="p-6">
      <div className="flex flex-wrap items-center justify-between gap-4"><div><p className="kicker">考试控制台</p><h2 className="mt-1 text-lg font-semibold">运行状态</h2></div><div className="flex gap-2"><Button size="sm" variant="secondary" onClick={() => void refresh()} disabled={busy}><RefreshCw size={14} />刷新</Button><Button size="sm" variant="secondary" onClick={() => void cancelExam()} disabled={busy || !canCancel}><Ban size={14} />取消考试</Button></div></div>
      {error ? <p className="mt-4 flex items-center gap-2 text-sm text-[var(--danger)]"><AlertTriangle size={14} />{error}</p> : null}
      <div className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-[8px] border border-[var(--border-soft)] bg-[var(--border-soft)] md:grid-cols-6">{metrics.map(([label, value]) => <div key={label} className="bg-[var(--surface-2)] p-4"><p className="text-xs text-[var(--text-muted)]">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p></div>)}</div>
      {monitor ? <p className="mt-3 text-xs text-[var(--text-muted)]">服务器时间 {monitor.serverNow} · 状态 {monitor.status}</p> : null}
    </Panel>

    <Panel className="p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><p className="kicker">候选人</p><h2 className="mt-1 text-lg font-semibold">考试资格</h2></div><div className="flex w-full max-w-xl gap-2"><Input value={candidateIds} onChange={(event) => setCandidateIds(event.target.value)} placeholder="用户 ID，多个以逗号分隔" /><Button onClick={() => void authorize()} disabled={busy}><UserPlus size={14} />授权</Button></div></div>
      <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-[var(--border-soft)] text-xs text-[var(--text-muted)]"><tr><th className="px-3 py-3">候选人</th><th className="px-3 py-3">资格</th><th className="px-3 py-3">作答状态</th><th className="px-3 py-3">风险</th><th className="px-3 py-3 text-right">操作</th></tr></thead><tbody>{monitor?.candidates.map((candidate) => <tr key={candidate.userId} className="border-b border-[var(--border-soft)]"><td className="px-3 py-3"><p className="font-medium">{candidate.nickName ?? candidate.userId}</p><p className="mt-1 text-xs text-[var(--text-muted)]">{candidate.email ?? candidate.userId}</p></td><td className="px-3 py-3"><Tag tone={candidate.authorized ? "success" : "default"}>{candidate.authorized ? "有效" : "已撤销"}</Tag></td><td className="px-3 py-3">{statusLabel(candidate.attemptStatus)}</td><td className="px-3 py-3">{candidate.riskLevel ?? 0}</td><td className="px-3 py-3 text-right">{candidate.attemptId ? <Button size="sm" variant="ghost" onClick={() => void showEvidence(candidate.attemptId!)}><ShieldCheck size={14} />证据</Button> : <Button size="sm" variant="ghost" onClick={() => void revoke(candidate.userId)} disabled={!candidate.authorized}><Users size={14} />撤销</Button>}</td></tr>)}</tbody></table></div>
    </Panel>

    <Panel className="p-6">
      <div className="flex items-center justify-between gap-4"><div><p className="kicker">成绩</p><h2 className="mt-1 text-lg font-semibold">复核与发布</h2></div><Button onClick={() => void release()} disabled={busy || !canRelease}><Send size={14} />发布成绩</Button></div>
      <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-[var(--border-soft)] text-xs text-[var(--text-muted)]"><tr><th className="px-3 py-3">考生</th><th className="px-3 py-3">状态</th><th className="px-3 py-3">成绩</th><th className="px-3 py-3">风险</th><th className="px-3 py-3 text-right">操作</th></tr></thead><tbody>{grades.map((grade) => <tr key={grade.gradeId} className="border-b border-[var(--border-soft)]"><td className="px-3 py-3">{grade.nickName ?? grade.userId}</td><td className="px-3 py-3">{statusLabel(grade.status)}</td><td className="px-3 py-3 font-mono">{grade.totalScore} / {grade.maxScore}</td><td className="px-3 py-3">{grade.riskLevel ?? 0}</td><td className="px-3 py-3 text-right"><Button size="sm" variant="ghost" onClick={() => void openReview(grade.attemptId)}><ClipboardCheck size={14} />阅卷</Button><Button size="sm" variant="ghost" onClick={() => void showEvidence(grade.attemptId)}><ShieldCheck size={14} />证据</Button></td></tr>)}</tbody></table></div>
    </Panel>

    {review ? <Panel className="p-6"><div className="flex items-center justify-between gap-4"><div><p className="kicker">人工阅卷</p><h2 className="mt-1 text-lg font-semibold">{review.candidateName}</h2></div><Button size="sm" variant="ghost" onClick={() => setReview(null)}>关闭</Button></div><div className="mt-5 space-y-6">{review.items.map((item) => <section key={item.versionQuestionId} className="border-t border-[var(--border-soft)] pt-5"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="font-medium">{item.questionOrder}. {item.title}</p><p className="mt-1 text-xs text-[var(--text-muted)]">{item.questionType} · {item.gradingMode === "MANUAL" ? "人工评分" : "自动评分"}</p></div><span className="font-mono text-sm">{item.awardedScore} / {item.maxScore}</span></div>{item.gradingRubric ? <div className="mt-4 border-l-2 border-[var(--accent)] pl-4"><p className="text-xs text-[var(--text-muted)]">评分标准</p><p className="mt-1 whitespace-pre-wrap text-sm leading-6">{item.gradingRubric}</p></div> : null}<pre className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap border border-[var(--border-soft)] bg-[var(--surface-2)] p-4 text-sm leading-7">{item.answerContent || "未作答"}</pre>{item.gradingMode === "MANUAL" ? <div className="mt-4 grid gap-3 md:grid-cols-[160px_1fr]"><label className="space-y-2"><span className="text-xs text-[var(--text-muted)]">得分</span><Input type="number" min="0" max={item.maxScore} value={item.awardedScore} onChange={(event) => setReview((current) => current ? { ...current, items: current.items.map((candidate) => candidate.versionQuestionId === item.versionQuestionId ? { ...candidate, awardedScore: Number(event.target.value) } : candidate) } : current)} /></label><label className="space-y-2"><span className="text-xs text-[var(--text-muted)]">评语</span><Input value={item.feedback ?? ""} onChange={(event) => setReview((current) => current ? { ...current, items: current.items.map((candidate) => candidate.versionQuestionId === item.versionQuestionId ? { ...candidate, feedback: event.target.value } : candidate) } : current)} /></label></div> : null}</section>)}</div><div className="mt-6 flex justify-end"><Button disabled={busy || !review.items.some((item) => item.gradingMode === "MANUAL")} onClick={() => void saveReview()}><ClipboardCheck size={14} />保存阅卷</Button></div></Panel> : null}

    {selectedAttempt ? <Panel className="p-6"><div className="flex items-center justify-between"><div><p className="kicker">证据时间线</p><h2 className="mt-1 text-lg font-semibold">Attempt {selectedAttempt}</h2></div><Button size="sm" variant="ghost" onClick={() => setSelectedAttempt(null)}>关闭</Button></div><div className="mt-5 divide-y divide-[var(--border-soft)] border-y border-[var(--border-soft)]">{evidence.length ? evidence.map((item, index) => <div key={`${item.serverTime}-${index}`} className="grid gap-2 py-4 md:grid-cols-[140px_1fr_100px]"><div><Tag tone={item.category === "INTEGRITY" ? "warning" : "default"}>{item.category}</Tag></div><div><p className="font-medium">{item.eventType}</p><p className="mt-1 break-all text-xs text-[var(--text-muted)]">{item.metadataJson || "无附加数据"}</p></div><div className="text-right text-xs text-[var(--text-muted)]"><p>风险 +{item.riskPoints}</p><p className="mt-1">{item.serverTime}</p></div></div>) : <p className="py-8 text-sm text-[var(--text-muted)]">暂无证据事件。</p>}</div></Panel> : null}
  </div>;
}
