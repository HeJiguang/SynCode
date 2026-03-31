import type { ApiEnvelope, TableEnvelope } from "../client";
import { requestJson, unwrapData, unwrapTable } from "../client";
import type { CodeLanguage, QuestionDetail, QuestionListItem } from "../contracts";
import { questionDetails, questions } from "../mock/problems";
import { normalizeDifficulty } from "../runtime";

type BackendQuestionRow = {
  questionId?: string | number | null;
  title: string;
  difficulty?: number | string | null;
};

type BackendExampleCase = {
  input?: string | null;
  output?: string | null;
  note?: string | null;
};

type BackendQuestionDetail = BackendQuestionRow & {
  timeLimit?: number | null;
  spaceLimit?: number | null;
  algorithmTag?: string | null;
  knowledgeTags?: string | null;
  estimatedMinutes?: number | null;
  trainingEnabled?: number | null;
  content?: string | null;
  defaultCode?: string | null;
  exampleCases?: BackendExampleCase[] | null;
};

const presets = Object.values(questionDetails);
const presetByTitle = new Map(presets.map((item) => [item.title, item]));
const presetById = new Map(presets.map((item) => [item.questionId, item]));

function cloneStarterCode(starterCode: Record<CodeLanguage, string>) {
  return {
    java: starterCode.java,
    cpp: starterCode.cpp,
    python: starterCode.python,
    go: starterCode.go,
    javascript: starterCode.javascript
  };
}

function splitContent(content?: string | null) {
  if (!content) return [];
  return content
    .split(/\r?\n\s*\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function splitTags(content?: string | null) {
  if (!content) return [];
  return content
    .split(/[;,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeQuestionId(row: BackendQuestionRow, fallbackId?: string) {
  if (row.questionId !== null && row.questionId !== undefined && row.questionId !== "") {
    return String(row.questionId);
  }
  if (fallbackId) return fallbackId;
  return row.title;
}

function mapQuestionRow(row: BackendQuestionRow, fallbackId?: string): QuestionListItem {
  const preset = presetByTitle.get(row.title) ?? presetById.get(fallbackId ?? "");

  return {
    questionId: normalizeQuestionId(row, fallbackId ?? preset?.questionId),
    title: row.title,
    difficulty: normalizeDifficulty(row.difficulty),
    tags: preset?.tags ?? [preset?.algorithmTag ?? "算法"],
    estimatedMinutes: preset?.estimatedMinutes ?? 20,
    trainingRecommended: preset?.trainingRecommended ?? false,
    acceptanceRate: preset?.acceptanceRate ?? "--",
    status: preset?.status ?? "未开始",
    heat: preset?.heat ?? 0
  };
}

function mapQuestionDetail(row: BackendQuestionDetail, tokenQuestionId?: string): QuestionDetail {
  const preset = presetByTitle.get(row.title) ?? presetById.get(tokenQuestionId ?? "");
  const base = mapQuestionRow(row, tokenQuestionId);
  const contentBlocks = splitContent(row.content);
  const knowledgeTags = splitTags(row.knowledgeTags);
  const starterCode = preset ? cloneStarterCode(preset.starterCode) : cloneStarterCode(questionDetails["two-sum"].starterCode);

  if (row.defaultCode) {
    starterCode.java = row.defaultCode;
  }

  const exampleCases =
    row.exampleCases?.map((item) => ({
      input: item.input ?? "",
      output: item.output ?? "",
      note: item.note ?? undefined
    })).filter((item) => item.input || item.output) ?? [];

  return {
    ...base,
    summary: preset?.summary ?? `${row.title} 的真实题目详情已从后端加载。`,
    content: contentBlocks.length > 0 ? contentBlocks : preset?.content ?? [],
    constraints: preset?.constraints ?? [],
    hints: preset?.hints ?? [],
    examples: exampleCases.length > 0 ? exampleCases : preset?.examples ?? [],
    starterCode,
    timeLimit: row.timeLimit ?? preset?.timeLimit ?? 1000,
    spaceLimit: row.spaceLimit ?? preset?.spaceLimit ?? 262144,
    algorithmTag: row.algorithmTag ?? preset?.algorithmTag ?? "算法",
    knowledgeTags: knowledgeTags.length > 0 ? knowledgeTags : preset?.knowledgeTags ?? []
  };
}

export async function fetchLiveProblemList() {
  const payload = await requestJson<TableEnvelope<BackendQuestionRow>>("/friend/question/semiLogin/list?pageNum=1&pageSize=20");
  return unwrapTable(payload).rows.map((item) => mapQuestionRow(item));
}

export async function fetchLiveHotProblemList() {
  const [list, hotPayload] = await Promise.all([
    fetchLiveProblemList(),
    requestJson<ApiEnvelope<BackendQuestionRow[]>>("/friend/question/semiLogin/hotList")
  ]);

  const idByTitle = new Map(list.map((item) => [item.title, item.questionId]));
  return unwrapData(hotPayload).map((item) => mapQuestionRow(item, idByTitle.get(item.title)));
}

export async function fetchLiveProblemDetail(questionId: string, token?: string | null) {
  const path = token
    ? `/friend/question/detail?questionId=${encodeURIComponent(questionId)}`
    : `/friend/question/semiLogin/detail?questionId=${encodeURIComponent(questionId)}`;
  const payload = await requestJson<ApiEnvelope<BackendQuestionDetail>>(path, { token });
  return mapQuestionDetail(unwrapData(payload), questionId);
}

export function getQuestionMockFallback(questionId?: string) {
  return questionDetails[questionId ?? ""] ?? questions[0] ? questionDetails["two-sum"] : questionDetails["two-sum"];
}
