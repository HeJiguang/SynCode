import type { SubmissionRecord } from "@aioj/api";

export type JudgeOutcomePayload = {
  requestId?: string | null;
  asyncStatus?: number | null;
  pass?: number | null;
  exeMessage?: string | null;
  lastError?: string | null;
};

export type JudgeResultDetail = {
  questionId?: string;
  requestId?: string;
  status: SubmissionRecord["status"];
  message?: string;
  failLine?: number;
};

export function extractFailLine(message?: string | null) {
  if (!message) return undefined;

  const chineseMatch = message.match(/第\s*(\d+)\s*行/);
  if (chineseMatch?.[1]) return Number(chineseMatch[1]);

  const englishMatch = message.match(/line\s+(\d+)/i);
  if (englishMatch?.[1]) return Number(englishMatch[1]);

  return undefined;
}

export function normalizeJudgeOutcome(payload: JudgeOutcomePayload): Omit<JudgeResultDetail, "questionId"> {
  const message = payload.lastError ?? payload.exeMessage ?? undefined;
  const failLine = extractFailLine(message);

  if (payload.asyncStatus === 0 || payload.pass === 3 || /判题中|judging|waiting/i.test(message ?? "")) {
    return {
      requestId: payload.requestId ?? undefined,
      status: "Pending",
      message,
      failLine
    };
  }

  if (payload.lastError || /compile/i.test(message ?? "")) {
    return {
      requestId: payload.requestId ?? undefined,
      status: "Compile Error",
      message,
      failLine
    };
  }

  if (payload.pass === 1) {
    return {
      requestId: payload.requestId ?? undefined,
      status: "Accepted",
      message,
      failLine
    };
  }

  return {
    requestId: payload.requestId ?? undefined,
    status: "Wrong Answer",
    message,
    failLine
  };
}

export function buildPendingSubmission(requestId: string, language: string): SubmissionRecord {
  return {
    submissionId: requestId,
    status: "Pending",
    language,
    runtime: "--",
    memory: "--",
    submittedAt: new Date().toISOString().slice(0, 19).replace("T", " "),
    notes: "等待判题结果..."
  };
}
