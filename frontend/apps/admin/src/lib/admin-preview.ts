export const previewAdminProfile = {
  nickName: "Preview Admin"
};

export const previewAdminDashboardSummary = {
  questionCount: 328,
  examCount: 24,
  noticeCount: 18,
  userCount: 1284
};

export const previewAdminQuestionRows = [
  {
    questionId: "101",
    title: "两数之和",
    difficulty: "Easy",
    trainingEnabled: true,
    updatedAt: "2026-03-29 15:18"
  },
  {
    questionId: "208",
    title: "合并区间",
    difficulty: "Medium",
    trainingEnabled: true,
    updatedAt: "2026-03-29 10:04"
  },
  {
    questionId: "309",
    title: "N 皇后",
    difficulty: "Hard",
    trainingEnabled: false,
    updatedAt: "2026-03-28 22:11"
  }
] as const;

export const previewAdminQuestionDetails = {
  "101": {
    questionId: "101",
    title: "两数之和",
    difficulty: 1,
    algorithmTag: "数组",
    knowledgeTags: "哈希表,双指针",
    estimatedMinutes: 15,
    trainingEnabled: 1,
    timeLimit: 1000,
    spaceLimit: 262144,
    content: "给定一个整数数组和目标值，返回和为目标值的两个下标。",
    questionCase:
      '[{"input":"nums = [2,7,11,15], target = 9","output":"[0,1]"},{"input":"nums = [3,2,4], target = 6","output":"[1,2]"}]',
    defaultCode:
      "class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        return new int[0];\n    }\n}",
    mainFuc: "twoSum"
  },
  "208": {
    questionId: "208",
    title: "合并区间",
    difficulty: 2,
    algorithmTag: "排序",
    knowledgeTags: "排序,区间合并",
    estimatedMinutes: 25,
    trainingEnabled: 1,
    timeLimit: 1000,
    spaceLimit: 262144,
    content: "合并所有重叠区间，并返回不重叠的区间集合。",
    questionCase:
      '[{"input":"[[1,3],[2,6],[8,10],[15,18]]","output":"[[1,6],[8,10],[15,18]]"}]',
    defaultCode:
      "class Solution {\n    public int[][] merge(int[][] intervals) {\n        return intervals;\n    }\n}",
    mainFuc: "merge"
  },
  "309": {
    questionId: "309",
    title: "N 皇后",
    difficulty: 3,
    algorithmTag: "回溯",
    knowledgeTags: "回溯,DFS,位运算",
    estimatedMinutes: 35,
    trainingEnabled: 0,
    timeLimit: 2000,
    spaceLimit: 262144,
    content: "返回所有不同的 N 皇后解法，帮助用户预览复杂题编辑页布局。",
    questionCase: '[{"input":"4","output":"[[\\".Q..\\",\\"...Q\\",\\"Q...\\",\\"..Q.\\"],[\\"..Q.\\",\\"Q...\\",\\"...Q\\",\\".Q..\\"]]"}]',
    defaultCode:
      "class Solution {\n    public List<List<String>> solveNQueens(int n) {\n        return new ArrayList<>();\n    }\n}",
    mainFuc: "solveNQueens"
  }
} as const;

export const previewAdminExamRows = [
  {
    examId: "2001",
    title: "周末算法冲刺测",
    status: "草稿",
    startTime: "2026-04-12 19:30:00",
    participantCount: 326
  },
  {
    examId: "2002",
    title: "数组与哈希阶段测",
    status: "已发布",
    startTime: "2026-04-08 20:00:00",
    participantCount: 87
  }
] as const;

export const previewAdminExamDetails = {
  "2001": {
    examId: "2001",
    title: "周末算法冲刺测",
    startTime: "2026-04-12 19:30:00",
    endTime: "2026-04-12 21:00:00",
    status: 0,
    examQuestionList: [
      { questionId: "101", title: "两数之和", difficulty: "Easy" },
      { questionId: "208", title: "合并区间", difficulty: "Medium" }
    ]
  },
  "2002": {
    examId: "2002",
    title: "数组与哈希阶段测",
    startTime: "2026-04-08 20:00:00",
    endTime: "2026-04-08 21:30:00",
    status: 1,
    examQuestionList: [
      { questionId: "101", title: "两数之和", difficulty: "Easy" },
      { questionId: "309", title: "N 皇后", difficulty: "Hard" }
    ]
  }
} as const;

export const previewAdminUserRows = [
  {
    userId: "10001",
    nickName: "Lin",
    email: "lin@example.com",
    status: "正常",
    direction: "后端开发 / 算法"
  },
  {
    userId: "10019",
    nickName: "Ming",
    email: "ming@example.com",
    status: "正常",
    direction: "算法训练 / 面试"
  },
  {
    userId: "10032",
    nickName: "Han",
    email: "han@example.com",
    status: "冻结",
    direction: "系统设计 / 工程"
  }
] as const;

export const previewAdminNoticeRows = [
  {
    noticeId: "3001",
    title: "训练系统升级预告",
    category: "公告",
    statusLabel: "已发布",
    pinned: true,
    isPublic: true,
    publishTime: "2026-04-05 10:00:00",
    createName: "运营组"
  },
  {
    noticeId: "3002",
    title: "周测题库更新",
    category: "更新",
    statusLabel: "草稿",
    pinned: false,
    isPublic: true,
    publishTime: "2026-04-04 18:30:00",
    createName: "题库组"
  }
] as const;

export const previewAdminNoticeDetails = {
  "3001": {
    noticeId: "3001",
    title: "训练系统升级预告",
    content: "本周将升级训练计划推荐和首页信息分层，便于你在纯前端阶段继续做界面优化与走查。",
    category: "公告",
    isPublic: 1,
    isPinned: 1,
    status: 1,
    publishTime: "2026-04-05 10:00:00"
  },
  "3002": {
    noticeId: "3002",
    title: "周测题库更新",
    content: "新增数组、哈希、回溯三个训练方向的周测内容，当前以预览数据形式展示。",
    category: "更新",
    isPublic: 1,
    isPinned: 0,
    status: 0,
    publishTime: "2026-04-04 18:30:00"
  }
} as const;
