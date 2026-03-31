import type { ApiEnvelope } from "../client";
import { requestJson, unwrapData } from "../client";
import type { SubmissionRecord } from "../contracts";
import { submissions } from "../mock/problems";

type BackendSubmissionRow = {
  submitId?: string | number | null;
  programType?: number | null;
  pass?: number | null;
  score?: number | null;
  exeMessage?: string | null;
  useTime?: number | null;
  useMemory?: number | null;
  createTime?: string | null;
  updateTime?: string | null;
};

function mapProgramType(programType?: number | null) {
  if (programType === 0) return "Java";
  if (programType === 1) return "C++";
  if (programType === 2) return "Go";
  return "Java";
}

function mapSubmissionStatus(row: BackendSubmissionRow): SubmissionRecord["status"] {
  if (row.pass === 1) return "Accepted";
  if (row.pass === 3 || row.pass === 2) return "Pending";

  const message = row.exeMessage?.toLowerCase() ?? "";
  if (message.includes("compile")) return "Compile Error";
  return "Wrong Answer";
}

function formatSubmittedAt(value?: string | null) {
  if (!value) return "刚刚";
  return value.replace("T", " ");
}

export async function fetchLiveSubmissionHistory(questionId?: string, token?: string | null, examId?: string | null) {
  const params = new URLSearchParams();
  if (questionId) params.set("questionId", questionId);
  if (examId) params.set("examId", examId);

  const payload = await requestJson<ApiEnvelope<BackendSubmissionRow[]>>(
    `/friend/user/question/submission/list?${params.toString()}`,
    { token }
  );

  return unwrapData(payload).map(
    (item, index): SubmissionRecord => ({
      submissionId: item.submitId ? String(item.submitId) : `submission-${index + 1}`,
      status: mapSubmissionStatus(item),
      language: mapProgramType(item.programType),
      runtime: item.useTime != null ? `${item.useTime} ms` : "--",
      memory: item.useMemory != null ? `${item.useMemory} KB` : "--",
      submittedAt: formatSubmittedAt(item.createTime ?? item.updateTime),
      notes: item.exeMessage ?? undefined
    })
  );
}

export function getSubmissionMockFallback() {
  return submissions;
}
