import { ApiError } from "@aioj/api";

type RouteErrorPayload = {
  status: number;
  body: {
    message: string;
    code?: number;
  };
};

export function resolveApiRouteError(error: unknown, fallbackMessage: string): RouteErrorPayload {
  if (error instanceof ApiError) {
    return {
      status: mapApiErrorStatus(error.code),
      body: {
        message: error.message || fallbackMessage,
        code: error.code
      }
    };
  }

  if (error instanceof SyntaxError) {
    return {
      status: 400,
      body: { message: "\u8bf7\u6c42\u4f53\u4e0d\u662f\u5408\u6cd5\u7684 JSON\u3002" }
    };
  }

  return {
    status: 502,
    body: {
      message: error instanceof Error && error.message ? error.message : fallbackMessage
    }
  };
}

function mapApiErrorStatus(code: number) {
  if (code >= 400 && code < 600) return code;
  if (code === 3001) return 401;
  if (code === 3106 || code === 3107) return 429;
  if ((code >= 3000 && code < 4000) || (code >= 4000 && code < 5000)) return 400;
  return 502;
}
