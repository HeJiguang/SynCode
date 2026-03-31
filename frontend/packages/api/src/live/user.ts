import type { ApiEnvelope } from "../client";
import { requestJson, unwrapData } from "../client";
import type { UserProfile } from "../contracts";
import { userProfile } from "../mock/user";

type BackendUserInfo = {
  nickName?: string | null;
  headImage?: string | null;
  email?: string | null;
};

type BackendUserDetail = {
  nickName?: string | null;
  headImage?: string | null;
  email?: string | null;
  schoolName?: string | null;
  majorName?: string | null;
  introduce?: string | null;
};

type BackendDashboardSummary = {
  solvedCount?: number | null;
  submissionCount?: number | null;
  streakDays?: number | null;
  heatmap?: Array<{
    studyDate?: string | null;
    submissionCount?: number | null;
  }> | null;
};

export async function fetchLiveUserProfile(token?: string | null) {
  const [infoPayload, detailPayload, summaryPayload] = await Promise.all([
    requestJson<ApiEnvelope<BackendUserInfo>>("/friend/user/info", { token }),
    requestJson<ApiEnvelope<BackendUserDetail>>("/friend/user/detail", { token }),
    requestJson<ApiEnvelope<BackendDashboardSummary>>("/friend/user/dashboard/summary", { token })
  ]);

  const info = unwrapData(infoPayload);
  const detail = unwrapData(detailPayload);
  const summary = unwrapData(summaryPayload);

  const heatmap = Object.fromEntries(
    (summary.heatmap ?? [])
      .filter((item) => item.studyDate)
      .map((item) => [String(item.studyDate), Number(item.submissionCount ?? 0)])
  );

  return {
    ...userProfile,
    headImage: detail.headImage ?? info.headImage ?? undefined,
    nickName: detail.nickName ?? info.nickName ?? "",
    email: detail.email ?? info.email ?? "",
    schoolName: detail.schoolName ?? "",
    majorName: detail.majorName ?? "",
    headline: detail.introduce ?? "",
    solvedCount: Number(summary.solvedCount ?? 0),
    submissionCount: Number(summary.submissionCount ?? 0),
    streakDays: Number(summary.streakDays ?? 0),
    heatmap,
    trainingHours: 0,
    recentFocus: ""
  } satisfies UserProfile;
}

export function getUserMockFallback() {
  return userProfile;
}
