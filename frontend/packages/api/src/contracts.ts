export type Difficulty = "Easy" | "Medium" | "Hard";
export type SolveStatus = "未开始" | "尝试中" | "已解决";
export type TrainingStatus = "待开始" | "进行中" | "已完成";
export type ExamStatus = "未开始" | "进行中" | "已结束";
export type MessageCategory = "公告" | "更新" | "训练" | "考试";
export type CodeLanguage = "java" | "cpp" | "python" | "go" | "javascript";

export type QuestionListItem = {
  questionId: string;
  title: string;
  difficulty: Difficulty;
  tags: string[];
  estimatedMinutes: number;
  trainingRecommended: boolean;
  acceptanceRate: string;
  status: SolveStatus;
  heat: number;
};

export type ExampleCase = {
  input: string;
  output: string;
  note?: string;
};

export type QuestionDetail = QuestionListItem & {
  summary: string;
  content: string[];
  constraints: string[];
  hints: string[];
  examples: ExampleCase[];
  starterCode: Record<CodeLanguage, string>;
  timeLimit: number;
  spaceLimit: number;
  algorithmTag: string;
  knowledgeTags: string[];
};

export type SubmissionRecord = {
  submissionId: string;
  status: "Accepted" | "Wrong Answer" | "Compile Error" | "Pending";
  language: string;
  runtime: string;
  memory: string;
  submittedAt: string;
  notes?: string;
};

export type AiMessage = {
  id: string;
  role: "user" | "assistant";
  title?: string;
  content: string;
};

export type TrainingTask = {
  taskId: string;
  title: string;
  status: TrainingStatus;
  focus: string;
  difficulty: Difficulty;
  rawStatus: number;
  taskType?: string;
  questionId?: string;
  examId?: string;
};

export type TrainingSnapshot = {
  title: string;
  direction: string;
  level: string;
  streakDays: number;
  weeklyGoal: string;
  completionRate: number;
  strengths: string[];
  weaknesses: string[];
  tasks: TrainingTask[];
};

export type ExamSummary = {
  examId: string;
  title: string;
  status: ExamStatus;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  questionCount: number;
};

export type ExamDetail = ExamSummary & {
  firstQuestionId?: string;
};

export type PublicMessage = {
  textId: string;
  title: string;
  content: string;
  category: MessageCategory;
  publishedAt: string;
  pinned: boolean;
};

export type UserProfile = {
  headImage?: string;
  nickName: string;
  email: string;
  schoolName: string;
  majorName: string;
  headline: string;
  solvedCount: number;
  submissionCount: number;
  trainingHours: number;
  streakDays: number;
  heatmap: Record<string, number>;
  recentFocus: string;
  timezone: string;
  preferredLanguage: CodeLanguage;
  notifyByEmail: boolean;
  editorTheme: "vs-dark";
  shortcuts: string[];
};

export type AdminMetric = {
  label: string;
  value: string;
  trend: string;
};

export type AdminQuestionRow = {
  questionId: string;
  title: string;
  difficulty: Difficulty;
  trainingEnabled: boolean;
  updatedAt: string;
};

export type AdminExamRow = {
  examId: string;
  title: string;
  status: ExamStatus;
  startTime: string;
  participantCount: number;
};

export type AdminUserRow = {
  userId: string;
  nickName: string;
  email: string;
  status: "正常" | "冻结";
  direction: string;
};
