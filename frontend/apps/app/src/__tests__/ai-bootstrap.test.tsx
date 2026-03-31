import assert from "node:assert/strict";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { AiMessage } from "@aioj/api";
import { getAiMessages } from "@aioj/api";

import { AiPanel } from "../components/ai-panel";

async function main() {
  const emptyMessages = await getAiMessages("two-sum");
  assert.equal(emptyMessages.length, 0);

  const emptyHtml = renderToStaticMarkup(
    <AiPanel messages={emptyMessages} questionId="two-sum" questionTitle="Two Sum" questionContent="Find two numbers." />
  );
  assert.match(emptyHtml, /No conversation history yet/);

  const seededMessages: AiMessage[] = [
    {
      id: "user-1",
      role: "user",
      content: "Why does this fail on duplicate values?"
    },
    {
      id: "assistant-1",
      role: "assistant",
      title: "Duplicate case",
      content: "Check the lookup order before writing into the hash map."
    }
  ];

  const historyHtml = renderToStaticMarkup(
    <AiPanel messages={seededMessages} questionId="two-sum" questionTitle="Two Sum" questionContent="Find two numbers." />
  );
  assert.match(historyHtml, /Duplicate case/);
  assert.match(historyHtml, /Check the lookup order before writing into the hash map\./);
  assert.doesNotMatch(historyHtml, /No conversation history yet/);
}

void main();
