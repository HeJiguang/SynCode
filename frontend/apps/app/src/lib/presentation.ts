import type { PublicMessage, TrainingTask } from "@aioj/api";

const TRAINING_STATUS_PENDING = "寰呭紑濮?" as const;
const TRAINING_STATUS_ACTIVE = "杩涜涓?" as const;
const TRAINING_STATUS_FINISHED = "宸插畬鎴?" as const;

const MESSAGE_CATEGORY_NOTICE = "鍏憡" as const;
const MESSAGE_CATEGORY_UPDATE = "鏇存柊" as const;
const MESSAGE_CATEGORY_TRAINING = "璁粌" as const;
const MESSAGE_CATEGORY_EXAM = "鑰冭瘯" as const;

export function getTrainingStatusLabel(task: Pick<TrainingTask, "rawStatus" | "status">) {
  const normalized = String(task.status ?? "");
  if (task.rawStatus === 2 || normalized === TRAINING_STATUS_FINISHED) return "已完成";
  if (task.rawStatus === 1 || normalized === TRAINING_STATUS_ACTIVE) return "进行中";
  return "待开始";
}

export function getTrainingStatusTone(task: Pick<TrainingTask, "rawStatus" | "status">) {
  const normalized = String(task.status ?? "");
  if (task.rawStatus === 2 || normalized === TRAINING_STATUS_FINISHED) return "success" as const;
  if (task.rawStatus === 1 || normalized === TRAINING_STATUS_ACTIVE) return "accent" as const;
  return "default" as const;
}

export function getMessageCategoryLabel(category: PublicMessage["category"]) {
  const normalized = String(category ?? "");
  if (normalized === MESSAGE_CATEGORY_UPDATE) return "更新";
  if (normalized === MESSAGE_CATEGORY_TRAINING) return "训练";
  if (normalized === MESSAGE_CATEGORY_EXAM) return "考试";
  return "公告";
}

export function getMessageCategoryTone(category: PublicMessage["category"]) {
  const normalized = String(category ?? "");
  if (normalized === MESSAGE_CATEGORY_EXAM) return "warning" as const;
  if (normalized === MESSAGE_CATEGORY_TRAINING) return "accent" as const;
  if (normalized === MESSAGE_CATEGORY_UPDATE) return "default" as const;
  return "accent" as const;
}

export function withFallback(value: string | undefined | null, fallback: string) {
  const normalized = String(value ?? "").trim();
  return normalized.length > 0 ? normalized : fallback;
}
