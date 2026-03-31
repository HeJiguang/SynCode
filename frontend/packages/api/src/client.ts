import { buildAuthHeaders } from "./auth";
import { resolveBackendBaseUrl } from "./runtime";

export type ApiEnvelope<T> = {
  code: number;
  msg: string;
  data: T;
};

export type TableEnvelope<T> = {
  code: number;
  msg: string;
  rows: T[];
  total: number;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public code: number,
    public payload?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function unwrapData<T>(payload: ApiEnvelope<T>) {
  if (payload.code !== 1000) {
    throw new ApiError(payload.msg || "Request failed", payload.code, payload);
  }
  return payload.data;
}

export function unwrapTable<T>(payload: TableEnvelope<T>) {
  if (payload.code !== 1000) {
    throw new ApiError(payload.msg || "Request failed", payload.code, payload);
  }
  return { rows: payload.rows, total: payload.total };
}

type RequestOptions = Omit<RequestInit, "headers"> & {
  token?: string | null;
  headers?: HeadersInit;
  baseUrl?: string;
};

export async function requestJson<T>(path: string, options: RequestOptions = {}) {
  const { baseUrl = resolveBackendBaseUrl(), token, headers, ...init } = options;
  const finalHeaders = new Headers();
  finalHeaders.set("Content-Type", "application/json");
  for (const [key, value] of Object.entries(buildAuthHeaders(token))) {
    if (value) finalHeaders.set(key, value);
  }
  if (headers) {
    const providedHeaders = new Headers(headers);
    providedHeaders.forEach((value, key) => {
      finalHeaders.set(key, value);
    });
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: finalHeaders,
    cache: "no-store"
  });

  const text = await response.text();
  if (!response.ok) {
    throw new ApiError(text || response.statusText, response.status);
  }
  return JSON.parse(text) as T;
}
