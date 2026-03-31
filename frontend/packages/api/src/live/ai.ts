import type { ApiEnvelope } from "../client";
import { requestJson, unwrapData } from "../client";
import type { AiMessage } from "../contracts";

type BackendAiMessage = {
  id?: string | number | null;
  messageId?: string | number | null;
  role?: string | null;
  title?: string | null;
  content?: string | null;
};

function normalizeRole(role?: string | null): AiMessage["role"] {
  return role === "user" ? "user" : "assistant";
}

export async function fetchLiveAiHistory(questionId: string, token?: string | null) {
  if (!token) return [];

  const payload = await requestJson<ApiEnvelope<BackendAiMessage[] | null>>(
    `/ai/history?questionId=${encodeURIComponent(questionId)}`,
    { token }
  );
  const rows = unwrapData(payload);
  if (!Array.isArray(rows)) return [];

  return rows.map((item, index): AiMessage => ({
    id: item.messageId ? String(item.messageId) : item.id ? String(item.id) : `ai-history-${index + 1}`,
    role: normalizeRole(item.role),
    title: item.title ?? undefined,
    content: item.content ?? ""
  }));
}
