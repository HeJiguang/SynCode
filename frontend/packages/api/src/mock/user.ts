import type { UserProfile } from "../contracts";

export const userProfile: UserProfile = {
  headImage: undefined,
  nickName: "Lin",
  email: "lin@example.com",
  schoolName: "华东理工大学",
  majorName: "软件工程",
  headline: "正在用 SynCode 把刷题和日常训练整理成一套稳定的学习工作流。",
  solvedCount: 126,
  submissionCount: 284,
  trainingHours: 48,
  streakDays: 12,
  heatmap: {},
  recentFocus: "哈希表 / 区间 / 设计题",
  timezone: "Asia/Shanghai",
  preferredLanguage: "java",
  notifyByEmail: true,
  editorTheme: "vs-dark",
  shortcuts: ["Ctrl + Enter 提交", "Alt + 1 切换题面", "Alt + 2 聚焦代码区"]
};
