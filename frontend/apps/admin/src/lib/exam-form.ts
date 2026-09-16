export type ExamFormValues = {
  title: string;
  startTime: string;
  latestStartTime: string;
  endTime: string;
  durationMinutes: string;
  timezone: string;
  maxFormalSubmissions: string;
  resultReleasePolicy: string;
  resultReleaseTime: string;
};

export type ExamFormErrors = Partial<Record<keyof ExamFormValues, string>>;

export function toExamApiDateTime(value: string) {
  return value ? `${value.replace("T", " ")}:00` : "";
}

export function buildExamCompositionPayload(items: Array<{
  questionId: string;
  score: string | number;
  required: boolean;
  questionType: string;
}>) {
  return items.map((item, index) => ({
    questionId: item.questionId,
    questionOrder: index + 1,
    score: Number(item.score),
    required: item.required,
    questionType: item.questionType
  }));
}

export function parseDecimalIds(value: string) {
  const parts = value.split(/[,\s]+/).map((item) => item.trim()).filter(Boolean);
  if (!parts.length || parts.some((item) => !/^\d+$/.test(item))) return null;
  return [...new Set(parts)];
}

export function validateExamForm(values: ExamFormValues, now = new Date()): ExamFormErrors {
  const errors: ExamFormErrors = {};
  const start = parseDate(values.startTime);
  const latestStart = parseDate(values.latestStartTime);
  const end = parseDate(values.endTime);
  const release = parseDate(values.resultReleaseTime);

  if (!values.title.trim()) errors.title = "请输入考试标题。";
  if (!start) errors.startTime = "请选择考试开始时间。";
  else if (start.getTime() <= now.getTime()) errors.startTime = "考试开始时间必须晚于当前时间。";
  if (!latestStart) errors.latestStartTime = "请选择最晚入场时间。";
  if (!end) errors.endTime = "请选择考试结束时间。";
  if (start && latestStart && latestStart.getTime() <= start.getTime()) {
    errors.latestStartTime = "最晚入场时间必须晚于开始时间。";
  }
  if (latestStart && end && latestStart.getTime() > end.getTime()) {
    errors.latestStartTime = "最晚入场时间不能晚于结束时间。";
  }
  if (start && end && end.getTime() <= start.getTime()) {
    errors.endTime = "考试结束时间必须晚于开始时间。";
  }
  if (!isPositiveInteger(values.durationMinutes)) errors.durationMinutes = "个人作答时长必须是正整数。";
  if (!isPositiveInteger(values.maxFormalSubmissions)) errors.maxFormalSubmissions = "正式提交上限必须是正整数。";
  if (!isValidTimezone(values.timezone)) errors.timezone = "请输入有效的 IANA 时区，例如 Asia/Shanghai。";
  if (values.resultReleasePolicy === "SCHEDULED") {
    if (!release) errors.resultReleaseTime = "请选择成绩发布时间。";
    else if (end && release.getTime() < end.getTime()) errors.resultReleaseTime = "成绩发布时间不能早于考试结束时间。";
  }
  return errors;
}

function parseDate(value: string) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function isPositiveInteger(value: string) {
  const number = Number(value);
  return Number.isInteger(number) && number > 0;
}

function isValidTimezone(value: string) {
  try {
    new Intl.DateTimeFormat("zh-CN", { timeZone: value }).format();
    return true;
  } catch {
    return false;
  }
}
