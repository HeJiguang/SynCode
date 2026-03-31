import { ACCESS_TOKEN_KEY } from "@aioj/api";
import { cookies } from "next/headers";

export async function getServerAccessToken() {
  try {
    const cookieStore = await cookies();
    return cookieStore.get(ACCESS_TOKEN_KEY)?.value ?? null;
  } catch {
    return null;
  }
}
