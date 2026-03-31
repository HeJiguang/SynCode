import type { ApiEnvelope } from "../client";
import { requestJson, unwrapData } from "../client";
import type { TrainingSnapshot } from "../contracts";
import { trainingSnapshot } from "../mock/training";

type BackendTrainingTask = {
  taskId?: string | number | null;
  taskType?: string | null;
  questionId?: string | number | null;
  examId?: string | number | null;
  titleSnapshot?: string | null;
  taskStatus?: number | null;
  knowledgeTagsSnapshot?: string | null;
};

type BackendTrainingCurrent = {
  planTitle?: string | null;
  planGoal?: string | null;
  planStatus?: number | null;
  aiSummary?: string | null;
  currentLevel?: string | null;
  targetDirection?: string | null;
  weakPoints?: string | null;
  strongPoints?: string | null;
  tasks?: BackendTrainingTask[] | null;
};

function normalizeTaskStatus(status?: number | null): TrainingSnapshot["tasks"][number]["status"] {
  if (status === 1) return "杩涜涓?" as TrainingSnapshot["tasks"][number]["status"];
  if (status === 2) return "宸插畬鎴?" as TrainingSnapshot["tasks"][number]["status"];
  return "寰呭紑濮?" as TrainingSnapshot["tasks"][number]["status"];
}

function splitPoints(value?: string | null) {
  if (!value) return [];
  return value
    .split(/[;,，、]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export async function fetchLiveTrainingSnapshot(token?: string | null) {
  const payload = await requestJson<ApiEnvelope<BackendTrainingCurrent>>("/friend/training/current", { token });
  const data = unwrapData(payload);

  const tasks = (data.tasks ?? []).map((task, index) => ({
    taskId: task.taskId ? String(task.taskId) : `task-${index + 1}`,
    taskType: task.taskType ?? undefined,
    questionId: task.questionId != null ? String(task.questionId) : undefined,
    examId: task.examId != null ? String(task.examId) : undefined,
    title: task.titleSnapshot ?? `训练任务 ${index + 1}`,
    status: normalizeTaskStatus(task.taskStatus),
    rawStatus: Number(task.taskStatus ?? 0),
    focus: task.knowledgeTagsSnapshot ?? "训练任务",
    difficulty: "Medium" as const
  }));
  const completedCount = (data.tasks ?? []).filter((task) => task.taskStatus === 2).length;
  const completionRate = tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0;

  return {
    title: data.planTitle ?? "当前暂无训练计划",
    direction: data.targetDirection ?? "待设置训练方向",
    level: data.currentLevel ?? "待评估",
    streakDays: 0,
    weeklyGoal: data.planGoal ?? "登录后生成个性化训练计划",
    completionRate,
    strengths: splitPoints(data.strongPoints),
    weaknesses: splitPoints(data.weakPoints),
    tasks
  } satisfies TrainingSnapshot;
}

export function getTrainingMockFallback() {
  return trainingSnapshot;
}
