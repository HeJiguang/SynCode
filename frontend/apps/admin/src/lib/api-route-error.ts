import { ApiError } from "@aioj/api";

type AdminApiErrorBody = {
  message: string;
  code?: number;
  details?: unknown;
};

export function resolveAdminApiError(error: unknown, fallbackMessage: string): {
  status: number;
  body: AdminApiErrorBody;
} {
  if (error instanceof ApiError) {
    const payload = error.payload && typeof error.payload === "object"
      ? error.payload as { details?: unknown }
      : undefined;
    return {
      status: mapApiErrorStatus(error.code),
      body: {
        message: error.message || fallbackMessage,
        code: error.code,
        ...(payload?.details === undefined ? {} : { details: payload.details })
      }
    };
  }

  if (error instanceof SyntaxError) {
    return { status: 400, body: { message: "请求内容格式不正确。" } };
  }

  return {
    status: 502,
    body: { message: error instanceof Error && error.message ? error.message : fallbackMessage }
  };
}

function mapApiErrorStatus(code: number) {
  if (code === 3001) return 401;
  if (code === 3106 || code === 3107 || code === 3231) return 429;
  if ([3203, 3226, 3237, 3238].includes(code)) return 404;
  if ([3225, 3232].includes(code)) return 403;
  if ([3222, 3224, 3228].includes(code)) return 410;
  if ([3234, 3239].includes(code)) return 422;
  if ([3220, 3221, 3223, 3227, 3229, 3230, 3233, 3235, 3236].includes(code)) return 409;
  if ((code >= 3000 && code < 5000) || (code >= 400 && code < 500)) return 400;
  return 502;
}
