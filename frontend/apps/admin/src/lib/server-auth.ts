import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { frontendPreviewMode } from "@aioj/config";

import { adminInternalPath } from "./paths";

export const ADMIN_ACCESS_TOKEN_COOKIE = "syncode_admin_access_token";

export async function getAdminAccessToken() {
  if (frontendPreviewMode) {
    return null;
  }
  const cookieStore = await cookies();
  return cookieStore.get(ADMIN_ACCESS_TOKEN_COOKIE)?.value ?? null;
}

export async function requireAdminAccessToken() {
  if (frontendPreviewMode) {
    return null;
  }
  const token = await getAdminAccessToken();
  if (!token) {
    redirect(adminInternalPath("/login"));
  }
  return token;
}
