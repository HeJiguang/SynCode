import * as React from "react";
import type { PublicMessage } from "@aioj/api";
import { Panel, Tag } from "@aioj/ui";

import { getMessageCategoryLabel, getMessageCategoryTone } from "../lib/presentation";

type AnnouncementCenterProps = {
  messages: PublicMessage[];
};

export function AnnouncementCenter({ messages }: AnnouncementCenterProps) {
  return (
    <Panel hoverable className="flex flex-col p-0">
      <div className="flex items-center justify-between border-b border-[var(--border-soft)] p-6">
        <div>
          <p className="kicker">Announcement Center</p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">系统公告</h3>
        </div>
        <Tag tone="accent">精选更新</Tag>
      </div>
      <div className="flex-1 divide-y divide-[var(--border-soft)]">
        {messages.map((msg) => (
          <div key={msg.textId} className="group p-6 transition-all duration-300 ease-out hover:bg-[var(--surface-1)]">
            <div className="flex items-center gap-3">
              <Tag tone={getMessageCategoryTone(msg.category)}>{getMessageCategoryLabel(msg.category)}</Tag>
              <span className="font-mono text-[13px] tabular-nums text-[var(--text-muted)]">{msg.publishedAt}</span>
            </div>
            <h4 className="mt-3 text-[15px] font-semibold text-[var(--text-primary)] transition-colors duration-300 ease-out group-hover:text-[var(--accent)]">
              {msg.title}
            </h4>
            <p className="mt-1.5 text-sm leading-relaxed text-[var(--text-secondary)]">{msg.content}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}
