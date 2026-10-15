import assert from "node:assert/strict";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { AiPanel } from "../components/ai-panel";

async function main() {
  const emptyHtml = renderToStaticMarkup(
    <AiPanel questionId="two-sum" questionTitle="Two Sum" questionContent="Find two numbers." />
  );
  assert.match(emptyHtml, /开始提问/);
}

void main();
