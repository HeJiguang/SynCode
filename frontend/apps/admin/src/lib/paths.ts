const ADMIN_BASE_PATH = "/admin";

function normalizePath(path: string) {
  if (!path) return "/";
  const withLeadingSlash = path.startsWith("/") ? path : `/${path}`;
  return withLeadingSlash === "/" ? "/" : withLeadingSlash.replace(/\/+$/, "");
}

export function adminInternalPath(path: string) {
  return normalizePath(path);
}

export function adminPublicPath(path: string) {
  const normalized = adminInternalPath(path);
  return normalized === "/" ? ADMIN_BASE_PATH : `${ADMIN_BASE_PATH}${normalized}`;
}

export function adminApiPath(path: string) {
  return adminPublicPath(`/api${normalizePath(path)}`);
}
