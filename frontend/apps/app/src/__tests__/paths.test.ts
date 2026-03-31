import assert from "node:assert/strict";

import { appApiPath, appInternalPath, appPublicPath } from "../lib/paths";

function main() {
  assert.equal(appInternalPath("/"), "/");
  assert.equal(appInternalPath("/login"), "/login");
  assert.equal(appInternalPath("workspace/1001"), "/workspace/1001");

  assert.equal(appPublicPath("/"), "/app");
  assert.equal(appPublicPath("/login"), "/app/login");
  assert.equal(appPublicPath("settings"), "/app/settings");

  assert.equal(appApiPath("/auth/login"), "/app/api/auth/login");
  assert.equal(appApiPath("training/generate"), "/app/api/training/generate");
}

main();
