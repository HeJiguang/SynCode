import { normalizeDifficulty, requestJson, type ApiEnvelope, type TableEnvelope, unwrapData, unwrapTable } from "@aioj/api";
import { frontendPreviewMode } from "@aioj/config";

import {
  previewAdminDashboardSummary,
  previewAdminExamDetails,
  previewAdminExamRows,
  previewAdminNoticeDetails,
  previewAdminNoticeRows,
  previewAdminProfile,
  previewAdminQuestionDetails,
  previewAdminQuestionRows,
  previewAdminUserRows
} from "./admin-preview";

type AdminInfo = {
  nickName?: string | null;
};

type BackendQuestionRow = {
  questionId?: string | number | null;
  title?: string | null;
  difficulty?: number | string | null;
  createTime?: string | null;
};

type BackendQuestionDetail = {
  questionId?: string | number | null;
  title?: string | null;
  difficulty?: number | null;
  algorithmTag?: string | null;
  knowledgeTags?: string | null;
  estimatedMinutes?: number | null;
  trainingEnabled?: number | null;
  timeLimit?: number | null;
  spaceLimit?: number | null;
  content?: string | null;
  questionCase?: string | null;
  defaultCode?: string | null;
  mainFuc?: string | null;
};

type BackendExamRow = {
  examId?: string | number | null;
  title?: string | null;
  status?: number | string | null;
  startTime?: string | null;
  createTime?: string | null;
};

type BackendExamDetail = {
  examId?: string | number | null;
  title?: string | null;
  startTime?: string | null;
  endTime?: string | null;
  status?: number | null;
  examQuestionList?: Array<{
    questionId?: string | number | null;
    title?: string | null;
    difficulty?: number | null;
  }> | null;
};

type BackendUserRow = {
  userId?: string | number | null;
  nickName?: string | null;
  email?: string | null;
  schoolName?: string | null;
  majorName?: string | null;
  status?: number | null;
};

type BackendNoticeRow = {
  noticeId?: string | number | null;
  title?: string | null;
  category?: string | null;
  isPublic?: number | null;
  isPinned?: number | null;
  status?: number | null;
  publishTime?: string | null;
  createTime?: string | null;
  createName?: string | null;
};

type BackendNoticeDetail = {
  noticeId?: string | number | null;
  title?: string | null;
  content?: string | null;
  category?: string | null;
  isPublic?: number | null;
  isPinned?: number | null;
  status?: number | null;
  publishTime?: string | null;
};

export type AdminQuestionDetail = {
  questionId: string;
  title: string;
  difficulty: number;
  algorithmTag: string;
  knowledgeTags: string;
  estimatedMinutes: number;
  trainingEnabled: number;
  timeLimit: number;
  spaceLimit: number;
  content: string;
  questionCase: string;
  defaultCode: string;
  mainFuc: string;
};

export type AdminExamDetail = {
  examId: string;
  title: string;
  startTime: string;
  endTime: string;
  status: number;
  examQuestionList: Array<{
    questionId: string;
    title: string;
    difficulty: ReturnType<typeof normalizeDifficulty>;
  }>;
};

export type AdminNoticeRow = {
  noticeId: string;
  title: string;
  category: string;
  statusLabel: string;
  pinned: boolean;
  isPublic: boolean;
  publishTime: string;
  createName: string;
};

export type AdminNoticeDetail = {
  noticeId: string;
  title: string;
  content: string;
  category: string;
  isPublic: number;
  isPinned: number;
  status: number;
  publishTime: string;
};

export type AdminDashboardSummary = {
  questionCount: number;
  examCount: number;
  noticeCount: number;
  userCount: number;
};

function usePreviewAdminData(token?: string | null) {
  return frontendPreviewMode || !token;
}

function normalizeExamPublishStatus(status?: number | string | null) {
  return status === 1 || status === "1" ? "已发布" : "草稿";
}

function normalizeNoticeStatus(status?: number | null) {
  return status === 1 ? "已发布" : "草稿";
}

export async function getAdminProfile(token?: string | null) {
  if (usePreviewAdminData(token)) {
    return previewAdminProfile;
  }
  const payload = await requestJson<ApiEnvelope<AdminInfo>>("/system/sysUser/info", { token });
  const data = unwrapData(payload);
  return {
    nickName: data.nickName ?? "管理员"
  };
}

export async function getAdminDashboardSummary(token?: string | null): Promise<AdminDashboardSummary> {
  if (usePreviewAdminData(token)) {
    return previewAdminDashboardSummary;
  }
  const [questionPayload, examPayload, userPayload, noticePayload] = await Promise.all([
    requestJson<TableEnvelope<BackendQuestionRow>>("/system/question/list?pageNum=1&pageSize=1", { token }),
    requestJson<TableEnvelope<BackendExamRow>>("/system/exam/list?pageNum=1&pageSize=1", { token }),
    requestJson<TableEnvelope<BackendUserRow>>("/system/user/list?pageNum=1&pageSize=1", { token }),
    requestJson<TableEnvelope<BackendNoticeRow>>("/system/notice/list?pageNum=1&pageSize=1", { token })
  ]);

  return {
    questionCount: unwrapTable(questionPayload).total,
    examCount: unwrapTable(examPayload).total,
    userCount: unwrapTable(userPayload).total,
    noticeCount: unwrapTable(noticePayload).total
  };
}

export async function getAdminQuestionRows(token?: string | null) {
  if (usePreviewAdminData(token)) {
    return previewAdminQuestionRows.map((item) => ({ ...item }));
  }
  const payload = await requestJson<TableEnvelope<BackendQuestionRow>>("/system/question/list?pageNum=1&pageSize=50", { token });
  return unwrapTable(payload).rows.map((item) => ({
    questionId: item.questionId ? String(item.questionId) : "--",
    title: item.title ?? "未命名题目",
    difficulty: normalizeDifficulty(item.difficulty),
    trainingEnabled: false,
    updatedAt: item.createTime ?? "--"
  }));
}

export async function getAdminQuestionDetail(token: string | null | undefined, questionId: string) {
  if (usePreviewAdminData(token)) {
    const previewQuestion = previewAdminQuestionDetails[questionId as keyof typeof previewAdminQuestionDetails] ?? previewAdminQuestionDetails["101"];
    return { ...previewQuestion };
  }
  const payload = await requestJson<ApiEnvelope<BackendQuestionDetail>>(`/system/question/detail?questionId=${encodeURIComponent(questionId)}`, { token });
  const data = unwrapData(payload);
  return {
    questionId: data.questionId ? String(data.questionId) : questionId,
    title: data.title ?? "",
    difficulty: Number(data.difficulty ?? 2),
    algorithmTag: data.algorithmTag ?? "",
    knowledgeTags: data.knowledgeTags ?? "",
    estimatedMinutes: Number(data.estimatedMinutes ?? 20),
    trainingEnabled: Number(data.trainingEnabled ?? 0),
    timeLimit: Number(data.timeLimit ?? 1000),
    spaceLimit: Number(data.spaceLimit ?? 262144),
    content: data.content ?? "",
    questionCase: data.questionCase ?? "[]",
    defaultCode: data.defaultCode ?? "",
    mainFuc: data.mainFuc ?? ""
  } satisfies AdminQuestionDetail;
}

export async function getAdminExamRows(token?: string | null) {
  if (usePreviewAdminData(token)) {
    return previewAdminExamRows.map((item) => ({
      examId: item.examId,
      title: item.title,
      status: item.status,
      startTime: item.startTime,
      participantCount: item.participantCount
    }));
  }
  const payload = await requestJson<TableEnvelope<BackendExamRow>>("/system/exam/list?pageNum=1&pageSize=50", { token });
  return unwrapTable(payload).rows.map((item) => ({
    examId: item.examId ? String(item.examId) : "--",
    title: item.title ?? "未命名考试",
    status: normalizeExamPublishStatus(item.status),
    startTime: item.startTime ?? item.createTime ?? "--",
    participantCount: 0
  }));
}

export async function getAdminExamDetail(token: string | null | undefined, examId: string) {
  if (usePreviewAdminData(token)) {
    const previewExam = previewAdminExamDetails[examId as keyof typeof previewAdminExamDetails] ?? previewAdminExamDetails["2001"];
    return {
      ...previewExam,
      examQuestionList: previewExam.examQuestionList.map((item) => ({ ...item }))
    };
  }
  const payload = await requestJson<ApiEnvelope<BackendExamDetail>>(`/system/exam/detail?examId=${encodeURIComponent(examId)}`, { token });
  const data = unwrapData(payload);
  return {
    examId: data.examId ? String(data.examId) : examId,
    title: data.title ?? "",
    startTime: data.startTime ?? "",
    endTime: data.endTime ?? "",
    status: Number(data.status ?? 0),
    examQuestionList: (data.examQuestionList ?? []).map((item) => ({
      questionId: item.questionId ? String(item.questionId) : "--",
      title: item.title ?? "未命名题目",
      difficulty: normalizeDifficulty(item.difficulty)
    }))
  } satisfies AdminExamDetail;
}

export async function getAdminUserRows(token?: string | null) {
  if (usePreviewAdminData(token)) {
    return previewAdminUserRows.map((item) => ({ ...item }));
  }
  const payload = await requestJson<TableEnvelope<BackendUserRow>>("/system/user/list?pageNum=1&pageSize=50", { token });
  return unwrapTable(payload).rows.map((item) => ({
    userId: item.userId ? String(item.userId) : "--",
    nickName: item.nickName ?? "未命名用户",
    email: item.email ?? "--",
    status: item.status === 1 ? ("冻结" as const) : ("正常" as const),
    direction: [item.schoolName, item.majorName].filter(Boolean).join(" / ") || "未填写"
  }));
}

export async function getAdminNoticeRows(token?: string | null): Promise<AdminNoticeRow[]> {
  if (usePreviewAdminData(token)) {
    return previewAdminNoticeRows.map((item) => ({ ...item }));
  }
  const payload = await requestJson<TableEnvelope<BackendNoticeRow>>("/system/notice/list?pageNum=1&pageSize=50", { token });
  return unwrapTable(payload).rows.map((item) => ({
    noticeId: item.noticeId ? String(item.noticeId) : "--",
    title: item.title ?? "未命名公告",
    category: item.category ?? "公告",
    statusLabel: normalizeNoticeStatus(item.status),
    pinned: item.isPinned === 1,
    isPublic: item.isPublic !== 0,
    publishTime: item.publishTime ?? item.createTime ?? "--",
    createName: item.createName ?? "系统"
  }));
}

export async function getAdminNoticeDetail(token: string | null | undefined, noticeId: string) {
  if (usePreviewAdminData(token)) {
    const previewNotice = previewAdminNoticeDetails[noticeId as keyof typeof previewAdminNoticeDetails] ?? previewAdminNoticeDetails["3001"];
    return { ...previewNotice };
  }
  const payload = await requestJson<ApiEnvelope<BackendNoticeDetail>>(`/system/notice/detail?noticeId=${encodeURIComponent(noticeId)}`, { token });
  const data = unwrapData(payload);
  return {
    noticeId: data.noticeId ? String(data.noticeId) : noticeId,
    title: data.title ?? "",
    content: data.content ?? "",
    category: data.category ?? "公告",
    isPublic: Number(data.isPublic ?? 1),
    isPinned: Number(data.isPinned ?? 0),
    status: Number(data.status ?? 0),
    publishTime: data.publishTime ?? ""
  } satisfies AdminNoticeDetail;
}
