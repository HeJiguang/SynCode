type JudgeRouteBody = {
  questionId?: string | null;
  examId?: string | null;
  customInputs?: string[];
};

const BACKEND_LONG_ID_RE = /^\d+$/;

export function normalizeBackendLongId(value?: string | null) {
  const normalized = value?.trim();
  if (!normalized || !BACKEND_LONG_ID_RE.test(normalized)) {
    return null;
  }
  return normalized;
}

export function normalizeOptionalBackendLongId(value?: string | null) {
  return normalizeBackendLongId(value) ?? undefined;
}

export function buildJudgeRunPayload(body: JudgeRouteBody, programType: number, userCode: string) {
  const questionId = normalizeBackendLongId(body.questionId);
  if (!questionId) {
    return null;
  }

  const payload: {
    questionId: string;
    examId?: string;
    programType: number;
    userCode: string;
    customInputs: string[];
  } = {
    questionId,
    programType,
    userCode,
    customInputs: body.customInputs ?? []
  };

  const examId = normalizeOptionalBackendLongId(body.examId);
  if (examId) {
    payload.examId = examId;
  }

  return payload;
}

export function buildJudgeSubmitPayload(body: JudgeRouteBody, programType: number, userCode: string) {
  const questionId = normalizeBackendLongId(body.questionId);
  if (!questionId) {
    return null;
  }

  const payload: {
    questionId: string;
    examId?: string;
    programType: number;
    userCode: string;
  } = {
    questionId,
    programType,
    userCode
  };

  const examId = normalizeOptionalBackendLongId(body.examId);
  if (examId) {
    payload.examId = examId;
  }

  return payload;
}

export function buildJudgeResultParams(questionId: string, requestId: string, examId?: string | null) {
  const normalizedQuestionId = normalizeBackendLongId(questionId);
  if (!normalizedQuestionId) {
    return null;
  }

  const params = new URLSearchParams({ questionId: normalizedQuestionId, requestId });
  const normalizedExamId = normalizeOptionalBackendLongId(examId);
  if (normalizedExamId) {
    params.set("examId", normalizedExamId);
  }
  return params;
}
