import assert from "node:assert/strict";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { AiArtifact } from "@aioj/api";

import { AiPanel } from "../components/ai-panel";

async function main() {
  const emptyHtml = renderToStaticMarkup(
    <AiPanel initialArtifacts={[]} questionId="two-sum" questionTitle="Two Sum" questionContent="Find two numbers." />
  );
  assert.match(emptyHtml, /开始提问/);

  const seededArtifacts: AiArtifact[] = [
    {
      artifactId: "art-1",
      runId: "run-1",
      artifactType: "diagnosis_report",
      title: "Duplicate case",
      summary: "The lookup order is inverted when duplicate values appear.",
      body: {
        answer: "Check the lookup order before writing into the hash map.",
        nextAction: "Trace the [3,3] sample before updating the map."
      },
      renderHint: "diagnosis",
      version: 1,
      createdAt: "2026-04-01T00:00:00Z"
    }
  ];

  const artifactHtml = renderToStaticMarkup(
    <AiPanel initialArtifacts={seededArtifacts} questionId="two-sum" questionTitle="Two Sum" questionContent="Find two numbers." />
  );
  assert.match(artifactHtml, /Duplicate case/);
  assert.match(artifactHtml, /Check the lookup order before writing into the hash map\./);
  assert.match(artifactHtml, /Trace the \[3,3\] sample before updating the map\./);
  assert.doesNotMatch(artifactHtml, /开始提问/);
}

void main();
