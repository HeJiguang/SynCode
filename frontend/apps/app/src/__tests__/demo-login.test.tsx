import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { POST as createDemoSession } from "../app/api/auth/demo/route";
import { TrainingActions } from "../components/training-actions";

async function main() {
  const previousEnabled = process.env.SYNCODE_DEMO_LOGIN_ENABLED;

  try {
    process.env.SYNCODE_DEMO_LOGIN_ENABLED = "false";
    const disabledResponse = await createDemoSession();
    assert.equal(disabledResponse.status, 404);

    process.env.SYNCODE_DEMO_LOGIN_ENABLED = "true";
    const enabledResponse = await createDemoSession();
    assert.equal(enabledResponse.status, 200);
    const setCookie = enabledResponse.headers.get("set-cookie") ?? "";
    assert.match(setCookie, /syncode_demo_session=1/);
    assert.match(setCookie, /HttpOnly/i);
    assert.match(setCookie, /SameSite=lax/i);
    assert.match(setCookie, /syncode_access_token=/);
    assert.match(setCookie, /Max-Age=0/);
  } finally {
    if (previousEnabled === undefined) delete process.env.SYNCODE_DEMO_LOGIN_ENABLED;
    else process.env.SYNCODE_DEMO_LOGIN_ENABLED = previousEnabled;
  }

  const trainingHtml = renderToStaticMarkup(
    <TrainingActions direction="algorithm_foundation" tasks={[]} demoMode />
  );
  assert.match(trainingHtml, /training-generate/);

  const testDir = path.dirname(fileURLToPath(import.meta.url));
  const loginSource = fs.readFileSync(path.resolve(testDir, "../app/login/page.tsx"), "utf8");
  const middlewareSource = fs.readFileSync(path.resolve(testDir, "../middleware.ts"), "utf8");
  const examPageSource = fs.readFileSync(path.resolve(testDir, "../app/exams/[examId]/page.tsx"), "utf8");
  const editorSource = fs.readFileSync(path.resolve(testDir, "../components/editor-panel.tsx"), "utf8");
  const aiSource = fs.readFileSync(path.resolve(testDir, "../components/ai-panel.tsx"), "utf8");
  const appShellSource = fs.readFileSync(path.resolve(testDir, "../components/app-shell.tsx"), "utf8");
  const logoutButtonSource = fs.readFileSync(path.resolve(testDir, "../components/logout-button.tsx"), "utf8");
  const aiRouteSources = [
    fs.readFileSync(path.resolve(testDir, "../app/api/ai/runs/route.ts"), "utf8"),
    fs.readFileSync(path.resolve(testDir, "../app/api/ai/runs/[runId]/events/route.ts"), "utf8"),
    fs.readFileSync(path.resolve(testDir, "../app/api/ai/runs/[runId]/artifacts/route.ts"), "utf8")
  ];

  assert.match(loginSource, /立即体验 Demo（无需注册）/);
  assert.match(loginSource, /一键进入测试账号/);
  assert.match(loginSource, /JSON\.stringify\(\{ email: testStudentEmail \}\)/);
  assert.doesNotMatch(loginSource, /邮箱直登/);
  assert.doesNotMatch(loginSource, /测试学生：/);
  assert.match(loginSource, /clearBrowserAccessToken/);
  assert.match(middlewareSource, /syncode_demo_session|DEMO_SESSION_KEY/);
  assert.match(middlewareSource, /SYNCODE_DEMO_LOGIN_ENABLED/);
  assert.match(examPageSource, /TrustedExamWorkspace examId=\{examId\} demoMode=\{demoMode\}/);
  assert.match(editorSource, /frontendPreviewMode \|\| demoMode/);
  assert.match(aiSource, /frontendPreviewMode \|\| demoMode/);
  assert.match(appShellSource, /当前使用测试数据/);
  assert.match(appShellSource, /LogoutButton demoMode=\{demoMode\}/);
  assert.doesNotMatch(appShellSource, /当前为测试体验模式：页面使用内置测试数据/);
  assert.match(logoutButtonSource, /退出体验/);
  assert.match(logoutButtonSource, /退出登录/);
  assert.match(logoutButtonSource, /\/auth\/logout/);
  assert.match(logoutButtonSource, /clearBrowserAccessToken/);
  for (const routeSource of aiRouteSources) {
    assert.match(routeSource, /if \(!token\)/);
    assert.match(routeSource, /status: 401/);
  }
}

void main();
