import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

async function main() {
  const testDir = path.dirname(fileURLToPath(import.meta.url));
  const source = fs.readFileSync(path.resolve(testDir, "../components/editor-panel.tsx"), "utf8");

  assert.match(source, /code-editor-frame flex min-h-\[260px\] flex-1 flex-col/);
  assert.match(source, /max-h-\[46vh\] shrink-0 overflow-auto border-b/);
  assert.match(source, /loader\.config\(\{ monaco \}\)/);
  assert.match(source, /editContext: false/);
  assert.match(source, /disposeInlineCompletions\(\)/);
  assert.doesNotMatch(source, /freeInlineCompletions\(\)/);
  assert.match(source, /aria-label="代码编辑器"/);
  assert.match(source, /setEditorFallback\(true\)/);
}

void main();
