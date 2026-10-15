type GovernanceOptions = {
  method?: "GET" | "POST";
  body?: unknown;
};

export type PromotionCandidate = {
  candidate_id: string;
  title: string;
  proposed_skill_name: string;
  category?: string | null;
  status: "discovered" | "reviewing" | "rejected" | "published";
  summary?: string | null;
  draft_content?: string | null;
  distinct_owner_count: number;
  member_count: number;
  usage_count_30d: number;
  min_similarity?: number | null;
  similarity_method: string;
  members?: Array<{
    source_ref: string;
    skill_version: string;
    owner_ref: string;
    similarity_score: number;
    redacted_summary?: string | null;
    usage_count_30d: number;
  }>;
};

export type LifecycleReview = {
  review_id: string;
  skill_id: string;
  skill_name: string;
  skill_version: string;
  reason: string;
  status: "pending" | "kept" | "archived";
  usage_count_30d: number;
  last_used_at?: string | null;
  create_time: string;
};

function baseUrl() {
  const value = process.env.SYNCODE_SKILL_GOVERNANCE_URL?.trim();
  if (!value) throw new Error("Skill 治理服务尚未配置。");
  return value.replace(/\/+$/, "");
}

function credential() {
  const value = process.env.SYNCODE_HERMES_PROVISION_KEY?.trim();
  if (!value) throw new Error("Skill 治理凭据尚未配置。");
  return value;
}

export async function governanceRequest<T>(path: string, options: GovernanceOptions = {}): Promise<T> {
  const response = await fetch(`${baseUrl()}${path}`, {
    method: options.method ?? "GET",
    headers: {
      Authorization: `Bearer ${credential()}`,
      ...(options.body === undefined ? {} : { "Content-Type": "application/json" })
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store"
  });
  const payload = await response.json().catch(() => ({ detail: "Skill 治理服务响应无效。" }));
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : "Skill 治理请求失败。");
  }
  return payload as T;
}

async function detailedCandidates(status: "discovered" | "reviewing") {
  const rows = await governanceRequest<PromotionCandidate[]>(
    `/internal/skill-governance/candidates?candidate_status=${status}&limit=100`
  );
  return Promise.all(rows.map((row) => governanceRequest<PromotionCandidate>(
    `/internal/skill-governance/candidates/${encodeURIComponent(row.candidate_id)}`
  )));
}

export async function getOpenPromotionCandidates() {
  const [discovered, reviewing] = await Promise.all([
    detailedCandidates("discovered"),
    detailedCandidates("reviewing")
  ]);
  return [...reviewing, ...discovered];
}

export async function getPendingLifecycleReviews() {
  return governanceRequest<LifecycleReview[]>(
    "/internal/skill-governance/lifecycle-reviews?review_status=pending&limit=100"
  );
}
