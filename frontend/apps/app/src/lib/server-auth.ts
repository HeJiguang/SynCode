import { ACCESS_TOKEN_KEY } from "@aioj/api";
import { frontendPreviewMode } from "@aioj/config";
import { cookies } from "next/headers";

export async function getServerAccessToken() {
  if (frontendPreviewMode) {
    return null;
  }
  try {
    const cookieStore = await cookies();
    return cookieStore.get(ACCESS_TOKEN_KEY)?.value ?? null;
  } catch {
    return null;
  }
}
