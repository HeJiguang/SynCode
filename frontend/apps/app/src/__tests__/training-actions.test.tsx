import assert from "node:assert/strict";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { TrainingActions } from "../components/training-actions";

function main() {
  const emptyHtml = renderToStaticMarkup(
    <TrainingActions
      direction="algorithm_foundation"
      tasks={[]}
    />
  );

  assert.match(emptyHtml, /data-testid="training-generate"/);
  assert.doesNotMatch(emptyHtml, /training-task-finish-/);
  assert.doesNotMatch(emptyHtml, /Actions/);

  const activeHtml = renderToStaticMarkup(
    <TrainingActions
      direction="graph_search"
      tasks={[
        {
          taskId: "task-1",
          title: "Two Sum",
          status: "寰呭紑濮?" as const,
          focus: "Array",
          difficulty: "Easy" as const,
          rawStatus: 0,
          taskType: "question",
          questionId: "1001"
        },
        {
          taskId: "task-2",
          title: "Week 1 checkpoint",
          status: "宸插畬鎴?" as const,
          focus: "Review",
          difficulty: "Medium" as const,
          rawStatus: 1,
          taskType: "test",
          examId: "2001"
        }
      ]}
    />
  );

  assert.match(activeHtml, /data-testid="training-task-finish-task-1"/);
  assert.match(activeHtml, /href="\/app\/workspace\/1001"/);
  assert.match(activeHtml, /href="\/app\/exams\/2001"/);
  assert.match(activeHtml, /去做题/);
  assert.match(activeHtml, /border-\[var\(--border-strong\)\]/);
  assert.match(activeHtml, /bg-\[var\(--surface-2\)\]/);
  assert.doesNotMatch(activeHtml, /training-task-finish-task-2/);
  assert.doesNotMatch(activeHtml, /璁粌鍔ㄤ綔/);
}

main();
