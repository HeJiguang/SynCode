import type { ExamDetail, ExamSummary, TrainingSnapshot } from "../contracts";

const TRAINING_STATUS_ACTIVE = "进行中" as TrainingSnapshot["tasks"][number]["status"];
const TRAINING_STATUS_PENDING = "待开始" as TrainingSnapshot["tasks"][number]["status"];
const EXAM_STATUS_UPCOMING = "未开始" as ExamSummary["status"];
const EXAM_STATUS_ACTIVE = "进行中" as ExamSummary["status"];
const EXAM_STATUS_FINISHED = "已结束" as ExamSummary["status"];

export const trainingSnapshot: TrainingSnapshot = {
  title: "哈希表与区间题稳定训练",
  direction: "后端开发 / 算法基础",
  level: "Lv.4 稳定提升期",
  streakDays: 12,
  weeklyGoal: "本周完成 8 题，并做 1 次阶段测复盘",
  completionRate: 68,
  strengths: ["哈希表模板切换比较稳", "基础数组题提交节奏较好", "最近复盘执行率明显提升"],
  weaknesses: ["复杂边界 case 仍容易漏掉", "区间题模板还没有完全固化", "回溯题的状态管理容易写乱"],
  tasks: [
    {
      taskId: "task-1",
      title: "完成两数之和并总结“先查后存”模板",
      status: TRAINING_STATUS_ACTIVE,
      focus: "补数映射 / 一次遍历",
      difficulty: "Easy",
      rawStatus: 0,
      taskType: "question",
      questionId: "two-sum"
    },
    {
      taskId: "task-2",
      title: "整理合并区间与插入区间的统一解法",
      status: TRAINING_STATUS_PENDING,
      focus: "排序 + 扫描",
      difficulty: "Medium",
      rawStatus: 0,
      taskType: "question",
      questionId: "merge-intervals"
    },
    {
      taskId: "task-3",
      title: "完成实验室招新编程体验考试",
      status: TRAINING_STATUS_PENDING,
      focus: "哈希 / 区间 / 拓扑排序",
      difficulty: "Hard",
      rawStatus: 0,
      taskType: "test",
      examId: "exam-sprint-01"
    }
  ]
};

export const examDetails: Record<string, ExamDetail> = {
  "exam-sprint-01": {
    examId: "exam-sprint-01",
    title: "实验室招新编程体验考试",
    status: EXAM_STATUS_ACTIVE,
    startTime: "现在可进入",
    endTime: "进入后 90 分钟",
    durationMinutes: 90,
    questionCount: 3,
    firstQuestionId: "two-sum"
  },
  "exam-checkpoint-02": {
    examId: "exam-checkpoint-02",
    title: "数组与哈希阶段测",
    status: EXAM_STATUS_UPCOMING,
    startTime: "2026-09-18 19:00",
    endTime: "2026-09-18 20:00",
    durationMinutes: 60,
    questionCount: 2,
    firstQuestionId: "merge-intervals"
  },
  "exam-review-03": {
    examId: "exam-review-03",
    title: "回溯专题复盘测",
    status: EXAM_STATUS_FINISHED,
    startTime: "2026-09-12 19:00",
    endTime: "2026-09-12 20:00",
    durationMinutes: 60,
    questionCount: 2,
    firstQuestionId: "n-queens"
  }
};

export const exams: ExamSummary[] = Object.values(examDetails).map(({ firstQuestionId: _firstQuestionId, ...exam }) => exam);
