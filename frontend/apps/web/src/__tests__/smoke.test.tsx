import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";

import HomePage from "../app/page";

async function main() {
  const html = renderToStaticMarkup(await HomePage());

  assert.match(html, /SynCode/);
  assert.match(html, /syncode-home-hero/);
  assert.match(html, /syncode-home-workbench/);
  assert.match(html, /syncode-home-canvas/);
  assert.match(html, /syncode-home-masthead/);
  assert.match(html, /syncode-home-metric/);
  assert.match(html, /<h1[^>]*>SynCode/);
  assert.doesNotMatch(html, /一个更稳的/);
  assert.doesNotMatch(html, /不是另一套首页皮肤/);
}

void main();
