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
  assert.match(dashboardHtml, /Hot Problems/);
  assert.match(dashboardHtml, /href="\/app"><div class="flex h-7 w-7/);
  assert.match(dashboardHtml, /href="\/app\/login"/);

  assert.match(workspaceHtml, /SynCode/);
  assert.match(workspaceHtml, /Agent Runtime/);
  assert.match(workspaceHtml, /Heat 98/);
}

void main();
