import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import ExamsPage from "../app/exams/page";
import ExamWorkspacePage from "../app/exams/[examId]/page";
import { SubmissionHeatmap } from "../components/submission-heatmap";

async function main() {
  const examsHtml = renderToStaticMarkup(await ExamsPage());
  const examWorkspaceHtml = renderToStaticMarkup(
    await ExamWorkspacePage({
      params: Promise.resolve({ examId: "exam-1" })
    })
  );
  const examWorkspaceSource = fs.readFileSync(
    path.resolve("src/app/exams/[examId]/page.tsx"),
    "utf8"
  );
  const heatmapHtml = renderToStaticMarkup(
    <SubmissionHeatmap
      weeks={2}
      data={{
        "2026-04-01": 1,
        "2026-04-02": 3,
        "2026-04-03": 6
      }}
    />
  );
  const globalStyles = fs.readFileSync(path.resolve("src/app/globals.css"), "utf8");

  assert.doesNotMatch(examsHtml, /text-zinc-50/);
  assert.match(examsHtml, /text-\[var\(--text-primary\)\]/);
  assert.doesNotMatch(examWorkspaceSource, /text-zinc-50|text-zinc-100|text-zinc-500|text-zinc-400/);
  assert.doesNotMatch(examWorkspaceSource, /border-white\/10|bg-white\/\[0\.03\]|bg-white\/\[0\.02\]/);
  assert.match(examWorkspaceHtml, /text-\[var\(--text-primary\)\]/);

  assert.match(heatmapHtml, /submission-heatmap-cell/);
  assert.match(heatmapHtml, /data-intensity="4"/);
  assert.match(globalStyles, /\.submission-heatmap-cell\[data-intensity="1"\]/);
  assert.match(globalStyles, /:root\.light\s+\.submission-heatmap-cell\[data-intensity="1"\]/);
}

void main();
