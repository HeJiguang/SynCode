import type { SubmissionRecord } from "@aioj/api";

import { normalizeJudgeOutcome } from "./judge-result";

export type BackendSubmissionRow = {
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

export function mapJudgeHistoryRow(row: BackendSubmissionRow, index: number): SubmissionRecord {
  const outcome = normalizeJudgeOutcome({
    pass: row.pass,
    exeMessage: row.exeMessage
  });

  return {
    submissionId: row.submitId ? String(row.submitId) : `submission-${index + 1}`,
    status: outcome.status,
    language: mapProgramType(row.programType),
    runtime: row.useTime != null ? `${row.useTime} ms` : "--",
    memory: row.useMemory != null ? `${row.useMemory} KB` : "--",
    submittedAt: (row.createTime ?? row.updateTime ?? "").replace("T", " ") || "鍒氬垰",
    notes: outcome.message
  };
}
