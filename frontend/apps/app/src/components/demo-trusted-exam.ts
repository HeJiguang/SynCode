import type { Access, Attempt, Question } from "./trusted-exam-workspace";

export type DemoExamLifecycle = {
  status: "IN_PROGRESS" | "SUBMITTED";
  serverNow: string;
  deadlineAt: string;
  submittedAt?: string;
};

const DEMO_DURATION_MINUTES = 90;

const questions: Question[] = [
  {
    versionQuestionId: "demo-registration-dedup",
    questionOrder: 1,
    score: 30,
    required: true,
    title: "报名名单去重统计",
    content: `实验室收到 n 条报名记录，每条记录是一个学号。请统计有效报名人数和重复提交次数。

同一个学号第一次出现计为有效报名，之后再次出现均计为重复提交。

输入格式
第一行一个整数 n（1 <= n <= 100000）。
接下来 n 行，每行一个只包含字母和数字的学号。

输出格式
输出两个整数，分别表示有效报名人数和重复提交次数。

样例输入
6
2026001
2026002
2026001
A003
2026002
B004

样例输出
4 2`,
    timeLimit: 1000,
    spaceLimit: 262144,
    allowedLanguages: ["java"],
    starterCode: {
      java: `import java.io.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        int n = Integer.parseInt(reader.readLine().trim());
        // 在这里完成你的实现
    }
}
`
    }
  },
  {
    versionQuestionId: "demo-merge-schedule",
    questionOrder: 2,
    score: 30,
    required: true,
    title: "合并实验室开放时段",
    content: `给定实验室当天的若干开放时段，请合并所有重叠或首尾相接的区间，输出最终开放安排。

每个区间 [start, end] 表示从 start 分钟到 end 分钟开放。若前一段的 end 等于后一段的 start，也应合并。

输入格式
第一行一个整数 n（1 <= n <= 100000）。
接下来 n 行，每行两个整数 start 和 end（0 <= start < end <= 1440）。

输出格式
第一行输出合并后的区间数量。
之后按开始时间升序输出每个区间。

样例输入
4
60 120
100 180
240 300
300 360

样例输出
2
60 180
240 360`,
    timeLimit: 1500,
    spaceLimit: 262144,
    allowedLanguages: ["java"],
    starterCode: {
      java: `import java.io.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws Exception {
        // 读取区间，排序后完成合并
    }
}
`
    }
  },
  {
    versionQuestionId: "demo-service-order",
    questionOrder: 3,
    score: 40,
    required: true,
    title: "服务启动顺序",
    content: `一个项目有 n 个服务和 m 条依赖关系。关系 a b 表示服务 a 必须在服务 b 之前启动。

请输出任意一个合法启动顺序；如果依赖中存在环，输出 IMPOSSIBLE。多个服务当前都可启动时，优先选择编号较小的服务。

输入格式
第一行两个整数 n 和 m（1 <= n, m <= 200000）。
接下来 m 行，每行两个整数 a 和 b（1 <= a, b <= n）。

输出格式
存在合法顺序时，输出 n 个服务编号；否则输出 IMPOSSIBLE。

样例输入
4 3
1 2
1 3
3 4

样例输出
1 2 3 4`,
    timeLimit: 2000,
    spaceLimit: 262144,
    allowedLanguages: ["java"],
    starterCode: {
      java: `import java.io.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws Exception {
        // 使用拓扑排序生成启动顺序
    }
}
`
    }
  }
];

function examTitle(examId: string) {
  return examId === "exam-sprint-01" ? "实验室招新编程体验考试" : "SynCode 编程体验考试";
}

export function createDemoExamAccess(examId: string, canResume = false): Access {
  const now = new Date();
  const latestStart = new Date(now.getTime() + 8 * 60 * 60 * 1000);
  return {
    title: examTitle(examId),
    description: "这是一份可完整操作的招新样卷，用来体验进入检查、整卷作答、自动保存和交卷流程。",
    serverNow: now.toISOString(),
    startAt: now.toISOString(),
    latestStartAt: latestStart.toISOString(),
    timezone: "Asia/Shanghai",
    durationMinutes: DEMO_DURATION_MINUTES,
    privacyNotice: "体验卷只在当前浏览器保存草稿与进度，不创建真实考试记录，不调用判题服务，也不采集诚信事件。",
    canStart: !canResume,
    canResume
  };
}

export function createDemoExamAttempt(examId: string, lifecycle?: DemoExamLifecycle): Attempt {
  const now = new Date();
  const state = lifecycle ?? {
    status: "IN_PROGRESS" as const,
    serverNow: now.toISOString(),
    deadlineAt: new Date(now.getTime() + DEMO_DURATION_MINUTES * 60 * 1000).toISOString()
  };
  return {
    attemptId: `demo-attempt-${examId}`,
    title: examTitle(examId),
    description: "实验室招新编程体验样卷",
    status: state.status,
    serverNow: state.serverNow,
    deadlineAt: state.deadlineAt,
    submittedAt: state.submittedAt,
    timezone: "Asia/Shanghai",
    questions,
    answers: []
  };
}
