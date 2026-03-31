import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";

import HomePage from "../app/page";

async function main() {
  const html = renderToStaticMarkup(await HomePage());

  assert.match(html, /SynCode/);
  assert.match(html, /开始体验/);
  assert.doesNotMatch(html, /进入控制台|控制台|Admin/);
}

void main();
