import assert from "node:assert/strict";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import ExamWorkspacePage from "../app/exams/[examId]/page";
import { mapJudgeHistoryRow } from "../lib/judge-history";

async function main() {
  const examHtml = renderToStaticMarkup(
    await ExamWorkspacePage({ params: Promise.resolve({ examId: "exam-checkpoint-02" }) })
  );

  assert.match(examHtml, /Heat 83/);
  assert.doesNotMatch(examHtml, /Heat 98/);
  assert.match(examHtml, /1 \/ 2/);

  const history = mapJudgeHistoryRow(
    {
      submitId: 9,
      programType: 0,
      pass: 1,
      exeMessage: "Accepted",
      useTime: 12,
      useMemory: 2048,
      createTime: "2026-03-31 09:45:00"
    },
    0
  );

  assert.equal(history.runtime, "12 ms");
  assert.equal(history.memory, "2048 KB");
  assert.equal(history.submittedAt, "2026-03-31 09:45:00");
}

void main();
