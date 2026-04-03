import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";

import DashboardPage from "../app/page";
import WorkspacePage from "../app/workspace/[questionId]/page";

async function main() {
  const dashboardHtml = renderToStaticMarkup(await DashboardPage());
  const workspaceHtml = renderToStaticMarkup(
    await WorkspacePage({ params: Promise.resolve({ questionId: "two-sum" }) })
  );

  assert.match(dashboardHtml, /SynCode/);
  assert.match(dashboardHtml, /Today/);
  assert.match(dashboardHtml, /当前训练主线/);
  assert.match(dashboardHtml, /href="\/app"><div class="flex h-8 w-8/);
  assert.match(dashboardHtml, /href="\/app\/login"/);

  assert.match(workspaceHtml, /SynCode/);
  assert.match(workspaceHtml, /题目说明/);
  assert.match(workspaceHtml, /热度 98/);
}

void main();
