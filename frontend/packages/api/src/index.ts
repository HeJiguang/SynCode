import type {
  AdminExamRow,
  AdminMetric,
  AdminQuestionRow,
  AdminUserRow,
  ExamDetail,
  ExamSummary,
  PublicMessage,
  QuestionDetail,
  QuestionListItem,
  SubmissionRecord,
  TrainingSnapshot,
  UserProfile
} from "./contracts";
import { adminExams, adminMetrics, adminQuestions, adminUsers } from "./mock/admin";
import { hotQuestions, questionDetails, questions } from "./mock/problems";
import { exams } from "./mock/training";
import { fetchLiveExamDetail, fetchLiveExamList, getExamMockFallback } from "./live/exams";
import { fetchLiveMessages, getMessageMockFallback } from "./live/messages";
import { fetchLiveHotProblemList, fetchLiveProblemDetail, fetchLiveProblemList } from "./live/questions";
import { fetchLiveSubmissionHistory, getSubmissionMockFallback } from "./live/submissions";
import { fetchLiveTrainingSnapshot, getTrainingMockFallback } from "./live/training";
import { fetchLiveUserProfile, getUserMockFallback } from "./live/user";

export * from "./contracts";
export * from "./auth";
export * from "./client";
export * from "./runtime";

export async function getProblemList(): Promise<QuestionListItem[]> {
  try {
    return await fetchLiveProblemList();
  } catch {
    return questions;
  }
}

export async function getHotProblemList(): Promise<QuestionListItem[]> {
  try {
    return await fetchLiveHotProblemList();
  } catch {
    return hotQuestions;
  }
}

export async function getProblemDetail(questionId: string, token?: string | null): Promise<QuestionDetail> {
  if (token) {
    return fetchLiveProblemDetail(questionId, token);
  }

  try {
    return await fetchLiveProblemDetail(questionId);
  } catch {
    return questionDetails[questionId] ?? questionDetails["two-sum"];
  }
}

export async function getSubmissionHistory(questionId?: string, token?: string | null, examId?: string | null): Promise<SubmissionRecord[]> {
  if (!token) return getSubmissionMockFallback();
  return fetchLiveSubmissionHistory(questionId, token, examId);
}

export async function getTrainingSnapshot(token?: string | null): Promise<TrainingSnapshot> {
  if (!token) return getTrainingMockFallback();
  return fetchLiveTrainingSnapshot(token);
}

export async function getExamList(): Promise<ExamSummary[]> {
  try {
    return await fetchLiveExamList();
  } catch {
    return exams;
  }
}

export async function getExamDetail(examId: string, token?: string | null): Promise<ExamDetail> {
  if (token) {
    return fetchLiveExamDetail(examId, token);
  }

  return getExamMockFallback(examId);
}

export async function getUserProfile(token?: string | null): Promise<UserProfile> {
  if (!token) return getUserMockFallback();
  return fetchLiveUserProfile(token);
}

export async function getPublicMessages(token?: string | null): Promise<PublicMessage[]> {
  try {
    return await fetchLiveMessages(token);
  } catch {
    return getMessageMockFallback();
  }
}

export async function getAdminMetrics(): Promise<AdminMetric[]> {
  return adminMetrics;
}

export async function getAdminQuestions(): Promise<AdminQuestionRow[]> {
  return adminQuestions;
}

export async function getAdminExams(): Promise<AdminExamRow[]> {
  return adminExams;
}

export async function getAdminUsers(): Promise<AdminUserRow[]> {
  return adminUsers;
}
