import assert from "node:assert/strict";

import { getAdminDashboardSummary } from "../lib/admin-api";

async function withMockFetch(
  resolver: (url: string) => unknown,
  run: () => Promise<void>
) {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = (async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const payload = resolver(url);
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  }) as typeof fetch;

  try {
    await run();
  } finally {
    globalThis.fetch = originalFetch;
  }
}

async function main() {
  await withMockFetch(
    (url) => {
      if (url.includes("/system/question/list")) {
        return {
          code: 1000,
          msg: "ok",
          rows: [{ questionId: 1, title: "Two Sum", difficulty: 1, createTime: "2026-03-31 09:00:00" }],
          total: 128
        };
      }

      if (url.includes("/system/exam/list")) {
        return {
          code: 1000,
          msg: "ok",
          rows: [{ examId: 1, title: "Weekly Sprint", status: 1, startTime: "2026-03-31 19:00:00" }],
          total: 9
        };
      }

      if (url.includes("/system/user/list")) {
        return {
          code: 1000,
          msg: "ok",
          rows: [{ userId: 1, nickName: "alice", email: "alice@example.com", schoolName: "SEU", majorName: "CS", status: 0 }],
          total: 2048
        };
      }

      if (url.includes("/system/notice/list")) {
        return {
          code: 1000,
          msg: "ok",
          rows: [{ noticeId: 1, title: "Notice", category: "公告", status: 1, isPublic: 1, isPinned: 0 }],
          total: 36
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    },
    async () => {
      const summary = await getAdminDashboardSummary("admin-token");

      assert.deepEqual(summary, {
        questionCount: 128,
        examCount: 9,
        noticeCount: 36,
        userCount: 2048
      });
    }
  );
}

void main();
