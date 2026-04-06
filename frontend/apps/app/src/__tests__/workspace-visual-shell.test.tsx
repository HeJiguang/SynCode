import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";

import WorkspacePage from "../app/workspace/[questionId]/page.tsx";

async function main() {
  const html = renderToStaticMarkup(
    await WorkspacePage({ params: Promise.resolve({ questionId: "two-sum" }) })
  );

  assert.match(html, /syncode-workspace-shell/);
  assert.match(html, /syncode-workspace-divider/);
  assert.match(html, /syncode-workspace-primary-resize-handle/);
  assert.match(html, /syncode-workspace-problem/);
  assert.match(html, /syncode-workspace-editor/);
  assert.match(html, /syncode-workspace-ai/);
  assert.doesNotMatch(html, /rounded-\[26px\]/);
}

void main();
