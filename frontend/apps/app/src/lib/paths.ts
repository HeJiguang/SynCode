const APP_BASE_PATH = "/app";

function normalizePath(path: string) {
  if (!path) return "/";
  const withLeadingSlash = path.startsWith("/") ? path : `/${path}`;
  return withLeadingSlash === "/" ? "/" : withLeadingSlash.replace(/\/+$/, "");
}

export function appInternalPath(path: string) {
  return normalizePath(path);
}

export function appPublicPath(path: string) {
  const normalized = appInternalPath(path);
  return normalized === "/" ? APP_BASE_PATH : `${APP_BASE_PATH}${normalized}`;
}

export function appApiPath(path: string) {
  return appPublicPath(`/api${normalizePath(path)}`);
}
