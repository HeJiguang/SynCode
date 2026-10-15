"use client";

import * as React from "react";
import { Archive, Check, RefreshCw, ShieldCheck, X } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button, Panel, Tag } from "@aioj/ui";

import { adminApiPath } from "../lib/paths";
import type { LifecycleReview, PromotionCandidate } from "../lib/skill-governance";

type Props = {
  initialCandidates: PromotionCandidate[];
  initialLifecycleReviews: LifecycleReview[];
};

async function responsePayload(response: Response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message ?? "操作失败。");
  return payload;
}

export function SkillGovernanceConsole({ initialCandidates, initialLifecycleReviews }: Props) {
  const router = useRouter();
  const [candidates, setCandidates] = React.useState(initialCandidates);
  const [reviews, setReviews] = React.useState(initialLifecycleReviews);
  const [busy, setBusy] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);

  React.useEffect(() => setCandidates(initialCandidates), [initialCandidates]);
  React.useEffect(() => setReviews(initialLifecycleReviews), [initialLifecycleReviews]);

  const reviewCandidate = async (
    candidate: PromotionCandidate,
    decision: "approve" | "reject",
    form?: HTMLFormElement
  ) => {
    setBusy(candidate.candidate_id);
    setNotice(null);
    try {
      const data = form ? new FormData(form) : null;
      const response = await fetch(
        adminApiPath(`/skills/governance/candidates/${candidate.candidate_id}`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            decision,
            proposed_skill_name: data?.get("name") || candidate.proposed_skill_name,
            category: data?.get("category") || candidate.category || "general",
            content: data?.get("content") || candidate.draft_content,
            note: data?.get("note") || undefined
          })
        }
      );
      await responsePayload(response);
      setCandidates((current) => current.filter((item) => item.candidate_id !== candidate.candidate_id));
      setNotice(decision === "approve" ? "平台 Skill 已发布。" : "候选已驳回。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "候选审核失败。");
    } finally {
      setBusy(null);
    }
  };

  const reviewLifecycle = async (review: LifecycleReview, decision: "keep" | "archive") => {
    setBusy(review.review_id);
    setNotice(null);
    try {
      const response = await fetch(adminApiPath(`/skills/governance/lifecycle/${review.review_id}`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision })
      });
      await responsePayload(response);
      setReviews((current) => current.filter((item) => item.review_id !== review.review_id));
      setNotice(decision === "archive" ? "平台 Skill 已归档。" : "平台 Skill 已保留。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "生命周期复审失败。");
    } finally {
      setBusy(null);
    }
  };

  const runHeartbeat = async () => {
    setBusy("heartbeat");
    setNotice(null);
    try {
      const response = await fetch(adminApiPath("/skills/governance/heartbeat"), { method: "POST" });
      const payload = await responsePayload(response);
      setNotice(`扫描 ${payload.profiles ?? 0} 个用户环境，发现 ${payload.clusters_found ?? 0} 个跨用户聚类。`);
      router.refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "治理心跳执行失败。");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
          <ShieldCheck size={16} />
          <span>{candidates.length} 个晋升候选 · {reviews.length} 个生命周期复审</span>
        </div>
        <Button onClick={() => void runHeartbeat()} disabled={busy !== null}>
          <RefreshCw size={15} />
          执行治理心跳
        </Button>
      </div>

      {notice ? (
        <div className="border-l-2 border-[var(--accent)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-secondary)]">
          {notice}
        </div>
      ) : null}

      <Panel className="overflow-hidden p-0" tone="strong">
        <div className="border-b border-[var(--border-soft)] px-5 py-4">
          <p className="kicker">晋升队列</p>
          <h2 className="mt-1 text-xl font-semibold">个人 Skill → 平台 Skill</h2>
        </div>
        <div className="divide-y divide-[var(--border-soft)]">
          {candidates.length ? candidates.map((candidate) => (
            <form
              key={candidate.candidate_id}
              className="space-y-4 px-5 py-5"
              onSubmit={(event) => {
                event.preventDefault();
                void reviewCandidate(candidate, "approve", event.currentTarget);
              }}
            >
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-[var(--text-primary)]">{candidate.title}</h3>
                    <Tag tone={candidate.status === "reviewing" ? "accent" : "warning"}>
                      {candidate.status === "reviewing" ? "待审核" : "待生成"}
                    </Tag>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">{candidate.summary || "暂无公共摘要"}</p>
                </div>
                <div className="grid shrink-0 grid-cols-3 gap-4 text-center text-xs text-[var(--text-muted)]">
                  <div><strong className="block text-lg text-[var(--text-primary)]">{candidate.distinct_owner_count}</strong>用户</div>
                  <div><strong className="block text-lg text-[var(--text-primary)]">{candidate.member_count}</strong>Skill</div>
                  <div><strong className="block text-lg text-[var(--text-primary)]">{candidate.usage_count_30d}</strong>调用</div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-xs font-medium text-[var(--text-muted)]">
                  Skill 名称
                  <input name="name" defaultValue={candidate.proposed_skill_name} className="mt-1.5 w-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-primary)]" />
                </label>
                <label className="text-xs font-medium text-[var(--text-muted)]">
                  分类
                  <input name="category" defaultValue={candidate.category ?? "general"} className="mt-1.5 w-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-primary)]" />
                </label>
              </div>

              <label className="block text-xs font-medium text-[var(--text-muted)]">
                平台版本内容
                <textarea
                  name="content"
                  defaultValue={candidate.draft_content ?? ""}
                  rows={14}
                  className="mt-1.5 w-full resize-y border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 font-mono text-xs leading-6 text-[var(--text-primary)]"
                />
              </label>

              <details className="border-t border-[var(--border-soft)] pt-3">
                <summary className="cursor-pointer text-sm font-medium text-[var(--text-secondary)]">查看脱敏来源节选</summary>
                <div className="mt-3 divide-y divide-[var(--border-soft)] border-y border-[var(--border-soft)]">
                  {(candidate.members ?? []).map((member) => (
                    <div key={member.source_ref} className="grid gap-2 py-3 text-xs md:grid-cols-[110px_90px_1fr]">
                      <span className="font-mono text-[var(--text-muted)]">用户 {member.owner_ref}</span>
                      <span className="text-[var(--text-secondary)]">v{member.skill_version}</span>
                      <pre className="whitespace-pre-wrap font-sans leading-5 text-[var(--text-secondary)]">{member.redacted_summary || "无摘要"}</pre>
                    </div>
                  ))}
                </div>
              </details>

              <label className="block text-xs font-medium text-[var(--text-muted)]">
                审核备注
                <input name="note" className="mt-1.5 w-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-primary)]" />
              </label>
              <div className="flex flex-wrap justify-end gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={busy !== null}
                  onClick={() => void reviewCandidate(candidate, "reject")}
                >
                  <X size={15} />
                  驳回
                </Button>
                <Button type="submit" disabled={busy !== null || !candidate.draft_content}>
                  <Check size={15} />
                  审核并发布
                </Button>
              </div>
            </form>
          )) : (
            <div className="px-5 py-10 text-sm text-[var(--text-muted)]">当前没有开放的跨用户 Skill 候选。</div>
          )}
        </div>
      </Panel>

      <Panel className="overflow-hidden p-0">
        <div className="border-b border-[var(--border-soft)] px-5 py-4">
          <p className="kicker">生命周期</p>
          <h2 className="mt-1 text-xl font-semibold">低使用平台 Skill 复审</h2>
        </div>
        <div className="divide-y divide-[var(--border-soft)]">
          {reviews.length ? reviews.map((review) => (
            <div key={review.review_id} className="flex flex-col gap-4 px-5 py-4 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">{review.skill_name}</h3>
                  <Tag>v{review.skill_version}</Tag>
                </div>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">{review.reason}</p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button variant="secondary" disabled={busy !== null} onClick={() => void reviewLifecycle(review, "keep")}>
                  <Check size={15} />
                  保留
                </Button>
                <Button variant="secondary" disabled={busy !== null} onClick={() => void reviewLifecycle(review, "archive")}>
                  <Archive size={15} />
                  归档
                </Button>
              </div>
            </div>
          )) : (
            <div className="px-5 py-10 text-sm text-[var(--text-muted)]">当前没有需要复审的平台 Skill。</div>
          )}
        </div>
      </Panel>
    </div>
  );
}
