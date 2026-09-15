import type { ApiEnvelope, TableEnvelope } from "../client";
import { requestJson, unwrapData, unwrapTable } from "../client";
import type { ExamDetail, ExamSummary } from "../contracts";
import { examDetails } from "../mock/training";

type BackendExamRow = {
  examId?: string | number | null;
  title?: string | null;
  startTime?: string | null;
  endTime?: string | null;
  examStartTime?: string | null;
  examEndTime?: string | null;
  durationMinutes?: number | null;
  questionCount?: number | null;
  status?: number | string | null;
};

const UPCOMING_EXAM_STATUS: ExamSummary["status"] = examDetails["exam-sprint-01"].status;
const ACTIVE_EXAM_STATUS: ExamSummary["status"] = examDetails["exam-checkpoint-02"].status;
const FINISHED_EXAM_STATUS: ExamSummary["status"] = examDetails["exam-review-03"].status;

function normalizeExamStatus(status?: string | number | null): ExamSummary["status"] {
  if (status === 2 || status === "2" || status === ACTIVE_EXAM_STATUS) return ACTIVE_EXAM_STATUS;
  if (status === 3 || status === "3" || status === 4 || status === "4"
      || status === 5 || status === "5" || status === FINISHED_EXAM_STATUS) return FINISHED_EXAM_STATUS;
  return UPCOMING_EXAM_STATUS;
}

function mapExamRow(row: BackendExamRow): ExamSummary {
  return {
    examId: row.examId ? String(row.examId) : "unknown-exam",
    title: row.title ?? "未命名考试",
    status: normalizeExamStatus(row.status),
    startTime: row.startTime ?? row.examStartTime ?? "--",
    endTime: row.endTime ?? row.examEndTime ?? "--",
    durationMinutes: row.durationMinutes ?? 0,
    questionCount: row.questionCount ?? 0
  };
}

function buildLiveFallbackExamDetail(examId: string): ExamDetail {
  return {
    examId,
    title: "考试暂不可用",
    status: UPCOMING_EXAM_STATUS,
    startTime: "--",
    endTime: "--",
    durationMinutes: 0,
    questionCount: 0,
    firstQuestionId: undefined
  };
}

export async function fetchLiveExamList() {
  const payload = await requestJson<TableEnvelope<BackendExamRow>>("/friend/exam/semiLogin/list?pageNum=1&pageSize=20");
  return unwrapTable(payload).rows.map(mapExamRow);
}

export async function fetchLiveExamDetail(examId: string, token?: string | null): Promise<ExamDetail> {
  const list = await fetchLiveExamList();
  const base = list.find((item) => item.examId === examId) ?? buildLiveFallbackExamDetail(examId);
  let firstQuestionId: string | undefined;

  if (token) {
    try {
      const firstQuestionPayload = await requestJson<ApiEnvelope<string>>(
        `/friend/exam/getFirstQuestion?examId=${encodeURIComponent(examId)}`,
        { token }
      );
      const resolvedQuestionId = unwrapData(firstQuestionPayload);
      if (resolvedQuestionId && /^\d+$/.test(String(resolvedQuestionId))) {
        firstQuestionId = String(resolvedQuestionId);
      }
    } catch {
      // Keep the exam shell available instead of falling back to mock string IDs.
    }
  }

  return {
    ...base,
    firstQuestionId
  };
}

export function getExamMockFallback(examId?: string): ExamDetail {
  return examDetails[examId ?? ""] ?? examDetails["exam-sprint-01"];
}
