import { ACCESS_TOKEN_KEY, DEMO_SESSION_KEY } from "@aioj/api";
import { frontendDemoLoginEnabled, frontendPreviewMode } from "@aioj/config";
import { cookies } from "next/headers";

export type ServerAuthSession = {
  token: string | null;
  demoMode: boolean;
};

export function isDemoLoginEnabled() {
  return frontendDemoLoginEnabled && process.env.SYNCODE_DEMO_LOGIN_ENABLED === "true";
}

export async function getServerAuthSession(): Promise<ServerAuthSession> {
  if (frontendPreviewMode) {
    return { token: null, demoMode: true };
  }
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get(ACCESS_TOKEN_KEY)?.value ?? null;
    const demoMode = !token && isDemoLoginEnabled() && cookieStore.get(DEMO_SESSION_KEY)?.value === "1";
    return { token, demoMode };
  } catch {
    return { token: null, demoMode: false };
  }
}

export async function getServerAccessToken() {
  return (await getServerAuthSession()).token;
}
