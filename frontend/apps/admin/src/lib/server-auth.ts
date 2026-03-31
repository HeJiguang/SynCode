import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { adminInternalPath } from "./paths";

export const ADMIN_ACCESS_TOKEN_COOKIE = "syncode_admin_access_token";

export async function getAdminAccessToken() {
  const cookieStore = await cookies();
  return cookieStore.get(ADMIN_ACCESS_TOKEN_COOKIE)?.value ?? null;
}

export async function requireAdminAccessToken() {
  const token = await getAdminAccessToken();
  if (!token) {
    redirect(adminInternalPath("/login"));
  }
  return token;
}
