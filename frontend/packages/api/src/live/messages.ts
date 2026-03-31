import type { TableEnvelope } from "../client";
import { requestJson, unwrapTable } from "../client";
import type { PublicMessage } from "../contracts";
import { publicMessages } from "../mock/messages";

type BackendMessageRow = {
  noticeId?: string | number | null;
  title?: string | null;
  content?: string | null;
  category?: string | null;
  isPinned?: number | null;
  publishTime?: string | null;
};

export async function fetchLiveMessages(_token?: string | null) {
  const payload = await requestJson<TableEnvelope<BackendMessageRow>>("/friend/message/semiLogin/list?pageNum=1&pageSize=10");
  const defaultCategory = publicMessages[0]!.category;

  return unwrapTable(payload).rows.map((item, index): PublicMessage => ({
    textId: item.noticeId ? String(item.noticeId) : `msg-${index + 1}`,
    title: item.title ?? "系统公告",
    content: item.content ?? "",
    category: (item.category as PublicMessage["category"] | null) ?? defaultCategory,
    publishedAt: item.publishTime?.replace("T", " ") ?? "刚刚",
    pinned: item.isPinned === 1
  }));
}

export function getMessageMockFallback() {
  return publicMessages;
}
