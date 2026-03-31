import type { AdminExamRow, AdminMetric, AdminQuestionRow, AdminUserRow } from "../contracts";

export const adminMetrics: AdminMetric[] = [
  { label: "题目总数", value: "328", trend: "本周新增 12" },
  { label: "活跃考生", value: "1,284", trend: "较上周 +8.2%" },
  { label: "训练计划生成", value: "462", trend: "今日已生成 39" },
  { label: "异常提交", value: "17", trend: "较昨日 -3" }
];

export const adminQuestions: AdminQuestionRow[] = [
  {
    questionId: "Q-101",
    title: "两数之和",
    difficulty: "Easy",
    trainingEnabled: true,
    updatedAt: "2026-03-29 15:18"
  },
  {
    questionId: "Q-208",
    title: "合并区间",
    difficulty: "Medium",
    trainingEnabled: true,
    updatedAt: "2026-03-29 10:04"
  },
  {
    questionId: "Q-309",
    title: "N 皇后",
    difficulty: "Hard",
    trainingEnabled: false,
    updatedAt: "2026-03-28 22:11"
  }
];

export const adminExams: AdminExamRow[] = [
  {
    examId: "E-001",
    title: "周末算法冲刺测",
    status: "未开始",
    startTime: "2026-03-30 19:30",
    participantCount: 326
  },
  {
    examId: "E-002",
    title: "数组与哈希阶段测",
    status: "进行中",
    startTime: "2026-03-29 20:00",
    participantCount: 87
  },
  {
    examId: "E-003",
    title: "回溯专题复盘测",
    status: "已结束",
    startTime: "2026-03-27 19:00",
    participantCount: 182
  }
];

export const adminUsers: AdminUserRow[] = [
  {
    userId: "U-001",
    nickName: "Lin",
    email: "lin@example.com",
    status: "正常",
    direction: "后端开发 / 算法"
  },
  {
    userId: "U-019",
    nickName: "Ming",
    email: "ming@example.com",
    status: "正常",
    direction: "算法训练 / 面试"
  },
  {
    userId: "U-032",
    nickName: "Han",
    email: "han@example.com",
    status: "冻结",
    direction: "系统设计 / 工程"
  }
];
