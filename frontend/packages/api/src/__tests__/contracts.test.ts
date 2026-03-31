import assert from "node:assert/strict";

import * as api from "../index";
import { fetchLiveMessages } from "../live/messages";
import { fetchLiveUserProfile } from "../live/user";

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
  const problems = await api.getProblemList();
  const detail = await api.getProblemDetail("1");

  assert.ok(problems.length >= 1);
  assert.ok(detail.questionId);
  assert.equal(typeof api.getHotProblemList, "function");
  assert.equal(typeof api.getPublicMessages, "function");

  assert.equal(api.resolveBackendBaseUrl("http://localhost:19090/"), "http://localhost:19090");
  assert.equal(api.resolveJudgeWebSocketUrl("http://localhost:19090"), "ws://localhost:19090/friend/ws/judge/result");
  assert.equal(api.unwrapData({ code: 1000, msg: "ok", data: { ok: true } }).ok, true);
  assert.equal(api.unwrapTable({ code: 1000, msg: "ok", rows: [1, 2], total: 2 }).rows.length, 2);
  assert.equal(api.normalizeDifficulty(1), "Easy");
  assert.equal(api.normalizeDifficulty(2), "Medium");
  assert.equal(api.normalizeDifficulty(3), "Hard");
  assert.equal(api.programTypeFromLanguage("java"), 0);
  assert.equal(api.programTypeFromLanguage("cpp"), 1);
  assert.equal(api.programTypeFromLanguage("go"), 2);
  assert.equal(api.isJudgeLanguageSupported("python"), false);

  await withMockFetch(
    (url) => {
      if (url.includes("/friend/message/semiLogin/list")) {
        return {
          code: 1000,
          msg: "ok",
          rows: [
            {
              noticeId: 9,
              title: "System Notice",
              content: "Real notice payload",
              category: "公告",
              isPinned: 0,
              publishTime: "2026-03-31 10:00:00"
            }
          ],
          total: 1
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    },
    async () => {
      const messages = await fetchLiveMessages();

      assert.equal(messages.length, 1);
      assert.equal(messages[0]?.textId, "9");
      assert.equal(messages[0]?.pinned, false);
      assert.equal(messages[0]?.publishedAt, "2026-03-31 10:00:00");
    }
  );

  await withMockFetch(
    (url) => {
      if (url.includes("/friend/user/info")) {
        return {
          code: 1000,
          msg: "ok",
          data: {
            nickName: "info-name",
            headImage: "https://cdn/avatar.png",
            email: "info@example.com"
          }
        };
      }

      if (url.includes("/friend/user/detail")) {
        return {
          code: 1000,
          msg: "ok",
          data: {
            nickName: "detail-name",
            headImage: "https://cdn/detail-avatar.png",
            email: "detail@example.com",
            schoolName: "SEU",
            majorName: "Software",
            introduce: "Focus on graphs"
          }
        };
      }

      if (url.includes("/friend/user/dashboard/summary")) {
        return {
          code: 1000,
          msg: "ok",
          data: {
            solvedCount: 14,
            submissionCount: 29,
            streakDays: 5,
            heatmap: [
              { studyDate: "2026-03-30", submissionCount: 3 },
              { studyDate: "2026-03-31", submissionCount: 2 }
            ]
          }
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    },
    async () => {
      const profile = await fetchLiveUserProfile("token");

      assert.equal(profile.nickName, "detail-name");
      assert.equal(profile.email, "detail@example.com");
      assert.equal(profile.solvedCount, 14);
      assert.equal(profile.submissionCount, 29);
      assert.equal(profile.streakDays, 5);
      assert.deepEqual(profile.heatmap, {
        "2026-03-30": 3,
        "2026-03-31": 2
      });
    }
  );
}

void main();
