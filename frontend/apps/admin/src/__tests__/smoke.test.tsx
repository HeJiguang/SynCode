import assert from "node:assert/strict";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import AdminLoginPage from "../app/login/page";

async function main() {
  const html = renderToStaticMarkup(React.createElement(AdminLoginPage));

  assert.match(html, /SynCode 管理端入口/);
  assert.match(html, /管理员登录/);
  assert.match(html, /登录后台/);
}

void main();
