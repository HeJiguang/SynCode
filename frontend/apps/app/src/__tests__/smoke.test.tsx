import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";

import DashboardPage from "../app/page.tsx";
import ExamsPage from "../app/exams/page.tsx";
import ProblemsPage from "../app/problems/page.tsx";
import WorkspacePage from "../app/workspace/[questionId]/page.tsx";

async function main() {
  const dashboardHtml = renderToStaticMarkup(await DashboardPage());
  const examsHtml = renderToStaticMarkup(await ExamsPage());
  const problemsHtml = renderToStaticMarkup(await ProblemsPage());
  const testDir = path.dirname(fileURLToPath(import.meta.url));
  const loginSource = fs.readFileSync(path.resolve(testDir, "../app/login/page.tsx"), "utf8");
  const workspaceHtml = renderToStaticMarkup(
    await WorkspacePage({ params: Promise.resolve({ questionId: "two-sum" }) })
  );

  assert.match(dashboardHtml, /SynCode/);
  assert.match(dashboardHtml, /href="\/app"><div class="flex h-10 w-10/);
  assert.match(dashboardHtml, /syncode-app-shell/);
  assert.match(dashboardHtml, /syncode-page-hero/);
  assert.match(dashboardHtml, /syncode-page-section/);
  assert.match(dashboardHtml, /syncode-dashboard-focus-list/);

  assert.match(problemsHtml, /题库/);
  assert.match(problemsHtml, /全部题目/);

  assert.match(problemsHtml, /syncode-app-sidebar/);
  assert.match(problemsHtml, /syncode-problem-board/);
  assert.match(problemsHtml, /syncode-filter-strip/);

  assert.match(examsHtml, /syncode-page-hero/);
  assert.match(examsHtml, /syncode-exam-list/);
  assert.match(examsHtml, /syncode-exam-entry/);

  assert.match(loginSource, /MascotCanvas/);
  assert.match(loginSource, /syncode-login-mascot/);
  assert.match(loginSource, /line-art-scene/);
  assert.match(loginSource, /mascotProfiles/);
  assert.match(loginSource, /hoverInfluence/);
  assert.match(loginSource, /anger/);
  assert.match(loginSource, /codeAvoid/);
  assert.match(loginSource, /upperBodyRotate/);
  assert.match(loginSource, /avoidPointer/);
  assert.match(loginSource, /requestAnimationFrame/);
  assert.match(loginSource, /pointerTargetRef/);
  assert.match(loginSource, /window\.addEventListener\("pointermove"/);
  assert.match(loginSource, /bodyTargetRef/);
  assert.match(loginSource, /headTargetRef/);
  assert.match(loginSource, /eyeTargetRef/);
  assert.match(loginSource, /fill="transparent"/);
  assert.match(loginSource, /pointerEvents="all"/);
  assert.match(loginSource, /bodyFollowWeight/);
  assert.match(loginSource, /headFollowWeight/);
  assert.match(loginSource, /eyeFollowWeight/);
  assert.match(loginSource, /syncode-track-wordmark/);
  assert.match(loginSource, /直接进入预览模式/);

  assert.match(loginSource, /rgba\(16,185,129,0\.78\)/);
  assert.match(loginSource, /rgba\(14,18,17,0\.96\)/);
  assert.doesNotMatch(loginSource, /rgba\(132,124,201,0\.76\)/);
  assert.doesNotMatch(loginSource, /rgba\(129,146,224,0\.8\)/);
  assert.doesNotMatch(loginSource, /rgba\(22,28,48,0\.98\)/);
  assert.doesNotMatch(loginSource, /rgba\(34,197,94,0\.82\)/);

  assert.match(workspaceHtml, /SynCode/);
  assert.match(workspaceHtml, /syncode-workspace-shell/);
  assert.match(workspaceHtml, /syncode-workspace-problem/);
  assert.match(workspaceHtml, /syncode-workspace-editor/);
  assert.match(workspaceHtml, /syncode-workspace-ai/);
  assert.doesNotMatch(workspaceHtml, /rounded-\[26px\]/);
}

void main();
