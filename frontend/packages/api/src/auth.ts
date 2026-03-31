export const ACCESS_TOKEN_KEY = "syncode_access_token";

export function getBrowserAccessToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setBrowserAccessToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
  document.cookie = `${ACCESS_TOKEN_KEY}=${encodeURIComponent(token)}; path=/`;
}

export function clearBrowserAccessToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  document.cookie = `${ACCESS_TOKEN_KEY}=; Max-Age=0; path=/`;
}

export function buildAuthHeaders(token?: string | null) {
  if (!token) return {};
  return { Authorization: token.startsWith("Bearer ") ? token : `Bearer ${token}` };
}
