import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

async function main() {
  const testDir = path.dirname(fileURLToPath(import.meta.url));
  const source = fs.readFileSync(path.resolve(testDir, "../components/editor-panel.tsx"), "utf8");

  assert.match(source, /code-editor-frame flex min-h-\[260px\] flex-1 flex-col/);
  assert.match(source, /max-h-\[46vh\] shrink-0 overflow-auto border-b/);
}

void main();
