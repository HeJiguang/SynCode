import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { Button, Input, Panel, Tabs, Tag } from "../index";

const panelHtml = renderToStaticMarkup(React.createElement(Panel, null, "Body"));
const inputHtml = renderToStaticMarkup(React.createElement(Input, { placeholder: "Email" }));
const buttonHtml = renderToStaticMarkup(React.createElement(Button, { variant: "secondary" }, "Open"));
const tagHtml = renderToStaticMarkup(React.createElement(Tag, null, "State"));
const tabsHtml = renderToStaticMarkup(
  React.createElement(Tabs, {
    tabs: [
      {
        id: "one",
        label: "One",
        content: "One"
      }
    ]
  })
);
const testDir = path.dirname(fileURLToPath(import.meta.url));
const tokensSource = fs.readFileSync(path.resolve(testDir, "../../../tokens/src/index.css"), "utf8");
const buttonSource = fs.readFileSync(path.resolve(testDir, "../components/button.tsx"), "utf8");

assert.match(panelHtml, /rounded-\[12px\]/);
assert.match(panelHtml, /shadow-none/);
assert.match(inputHtml, /rounded-\[8px\]/);
assert.match(buttonHtml, /rounded-\[8px\]/);
assert.match(tagHtml, /tracking-\[0\.12em\]/);
assert.match(tagHtml, /whitespace-nowrap/);
assert.match(tabsHtml, /border-b border-\[var\(--border-soft\)\] bg-\[var\(--surface-1\)\]/);
assert.match(tokensSource, /--accent:\s*var\(--brand-600\);/);
assert.doesNotMatch(tokensSource, /--accent:\s*var\(--brand-400\);/);
assert.match(buttonSource, /hover:bg-\[var\(--accent-strong\)\]/);
assert.doesNotMatch(buttonSource, /hover:bg-\[var\(--brand-500\)\]/);
