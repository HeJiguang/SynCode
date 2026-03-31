import assert from "node:assert/strict";

import { adminApiPath, adminInternalPath, adminPublicPath } from "../lib/paths";

function main() {
  assert.equal(adminInternalPath("/"), "/");
  assert.equal(adminInternalPath("/login"), "/login");
  assert.equal(adminInternalPath("questions"), "/questions");

  assert.equal(adminPublicPath("/"), "/admin");
  assert.equal(adminPublicPath("/login"), "/admin/login");
  assert.equal(adminPublicPath("questions"), "/admin/questions");

  assert.equal(adminApiPath("/auth/login"), "/admin/api/auth/login");
  assert.equal(adminApiPath("users/status"), "/admin/api/users/status");
}

main();
