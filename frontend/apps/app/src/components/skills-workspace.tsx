"use client";

import * as React from "react";
import { Archive, History, Plus, RotateCcw, Save } from "lucide-react";

import { Button, Panel, Tag } from "@aioj/ui";

import { appApiPath } from "../lib/paths";

type NativeSkill = {
  name: string;
  description?: string;
  category?: string | null;
  enabled?: boolean;
  usage?: number;
  provenance?: "external" | "agent" | "hub" | "bundled";
};

type RegistrySkill = {
  skill_id: string;
  skill_name: string;
  display_name?: string | null;
  description?: string | null;
  category?: string | null;
  lifecycle_status: "active" | "archived" | "stale";
  current_version: string;
  usage_count_30d: number;
  last_used_at?: string | null;
};

type SkillVersion = {
  version: string;
  content_hash: string;
  create_time: string;
};

const NEW_SKILL = `---
name: my-skill
description: Use when a recurring task needs a personal procedure.
---

# Personal procedure

1. Check the current context.
2. Apply the reusable steps.
3. Verify the result.
`;

async function jsonResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message ?? payload.detail ?? "Skill 操作失败。");
  return payload as T;
}

export function SkillsWorkspace() {
  const [nativeSkills, setNativeSkills] = React.useState<NativeSkill[]>([]);
  const [registry, setRegistry] = React.useState<RegistrySkill[]>([]);
  const [selected, setSelected] = React.useState<string | null>(null);
  const [content, setContent] = React.useState(NEW_SKILL);
  const [category, setCategory] = React.useState("personal");
  const [versions, setVersions] = React.useState<SkillVersion[]>([]);
  const [creating, setCreating] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [notice, setNotice] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    setBusy(true);
    try {
      const [nativeResponse, registryResponse] = await Promise.all([
        fetch(appApiPath("/ai/hermes/skills"), { cache: "no-store" }),
        fetch(appApiPath("/ai/hermes/skills/registry"), { cache: "no-store" })
      ]);
      setNativeSkills(await jsonResponse<NativeSkill[]>(nativeResponse));
      setRegistry(await jsonResponse<RegistrySkill[]>(registryResponse));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Skill 列表加载失败。");
    } finally {
      setBusy(false);
    }
  }, []);

  React.useEffect(() => { void load(); }, [load]);

  const openSkill = async (name: string, create = false) => {
    setSelected(name);
    setCreating(create);
    setNotice(null);
    if (create) {
      setContent(NEW_SKILL);
      setVersions([]);
      return;
    }
    setBusy(true);
    try {
      const native = nativeSkills.find((item) => item.name === name);
      if (native) {
        const response = await fetch(`${appApiPath("/ai/hermes/skills/content")}?name=${encodeURIComponent(name)}`);
        const payload = await jsonResponse<{ content: string }>(response);
        setContent(payload.content);
      }
      const registered = registry.find((item) => item.skill_name === name);
      if (registered) {
        const versionResponse = await fetch(
          appApiPath(`/ai/hermes/skills/registry/${encodeURIComponent(name)}`),
          { cache: "no-store" }
        );
        setVersions(await jsonResponse<SkillVersion[]>(versionResponse));
        setCategory(registered.category ?? "personal");
      } else {
        setVersions([]);
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Skill 内容加载失败。");
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const match = content.match(/^---[\s\S]*?\nname:\s*([a-z0-9][a-z0-9_-]{0,63})\s*$/m);
      const name = match?.[1] ?? "";
      const response = await fetch(
        appApiPath(creating ? "/ai/hermes/skills" : "/ai/hermes/skills/content"),
        {
          method: creating ? "POST" : "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(creating ? { name, category, content } : { name: selected, content })
        }
      );
      await jsonResponse(response);
      const savedName = name || selected;
      setSelected(savedName);
      setCreating(false);
      await load();
      if (savedName) {
        const versionResponse = await fetch(
          appApiPath(`/ai/hermes/skills/registry/${encodeURIComponent(savedName)}`),
          { cache: "no-store" }
        );
        setVersions(await jsonResponse<SkillVersion[]>(versionResponse));
      }
      setNotice("个人 Skill 已保存并生成新版本。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Skill 保存失败。");
    } finally {
      setBusy(false);
    }
  };

  const changeLifecycle = async (name: string, action: "archive" | "restore") => {
    setBusy(true);
    setNotice(null);
    try {
      const response = await fetch(appApiPath("/ai/hermes/skills/lifecycle"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, skill_name: name })
      });
      await jsonResponse(response);
      await load();
      setSelected(null);
      setNotice(action === "archive" ? "个人 Skill 已归档。" : "个人 Skill 已恢复。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Skill 状态更新失败。");
    } finally {
      setBusy(false);
    }
  };

  const rollback = async (name: string, version: string) => {
    setBusy(true);
    setNotice(null);
    try {
      const response = await fetch(appApiPath("/ai/hermes/skills/rollback"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_name: name, version })
      });
      await jsonResponse(response);
      await load();
      await openSkill(name);
      setNotice(`已从 ${version} 恢复，并生成新的当前版本。`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Skill 回滚失败。");
    } finally {
      setBusy(false);
    }
  };

  const activePersonal = registry.filter((item) => item.lifecycle_status === "active");
  const archivedPersonal = registry.filter((item) => item.lifecycle_status === "archived");
  const platformSkills = nativeSkills.filter((item) => item.provenance === "external");
  const selectedNative = nativeSkills.find((item) => item.name === selected);
  const canEdit = creating || (selectedNative && selectedNative.provenance !== "external");

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm text-[var(--text-secondary)]">
          {activePersonal.length} 个个人 Skill · {platformSkills.length} 个平台 Skill
        </div>
        <Button onClick={() => void openSkill("new", true)} disabled={busy}>
          <Plus size={15} />
          新建个人 Skill
        </Button>
      </div>

      {notice ? <div className="border-l-2 border-[var(--accent)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-secondary)]">{notice}</div> : null}

      <div className="grid gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
        <Panel className="overflow-hidden p-0">
          <div className="border-b border-[var(--border-soft)] px-4 py-3"><h2 className="font-semibold">个人 Skill</h2></div>
          <div className="divide-y divide-[var(--border-soft)]">
            {activePersonal.map((item) => (
              <button key={item.skill_id} type="button" onClick={() => void openSkill(item.skill_name)} className="w-full px-4 py-3 text-left hover:bg-[var(--surface-2)]">
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-medium">{item.display_name || item.skill_name}</span>
                  <Tag tone="success">v{item.current_version}</Tag>
                </div>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-[var(--text-muted)]">{item.description || "暂无描述"}</p>
              </button>
            ))}
            {archivedPersonal.map((item) => (
              <div key={item.skill_id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0"><p className="truncate text-sm text-[var(--text-muted)]">{item.skill_name}</p><Tag>已归档</Tag></div>
                <Button size="sm" variant="ghost" onClick={() => void changeLifecycle(item.skill_name, "restore")} disabled={busy} title="恢复 Skill"><RotateCcw size={14} /></Button>
              </div>
            ))}
          </div>
          <div className="border-y border-[var(--border-soft)] px-4 py-3"><h2 className="font-semibold">平台 Skill</h2></div>
          <div className="divide-y divide-[var(--border-soft)]">
            {platformSkills.map((item) => (
              <button key={item.name} type="button" onClick={() => void openSkill(item.name)} className="w-full px-4 py-3 text-left hover:bg-[var(--surface-2)]">
                <div className="flex items-center justify-between gap-3"><span className="truncate text-sm font-medium">{item.name}</span><Tag tone="accent">平台</Tag></div>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-[var(--text-muted)]">{item.description || "暂无描述"}</p>
              </button>
            ))}
          </div>
        </Panel>

        <Panel className="p-5" tone="strong">
          {selected ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div><p className="kicker">{canEdit ? "个人版本" : "平台只读"}</p><h2 className="mt-1 text-xl font-semibold">{creating ? "新建 Skill" : selected}</h2></div>
                <div className="flex gap-2">
                  {!creating && canEdit ? <Button variant="secondary" onClick={() => void changeLifecycle(selected, "archive")} disabled={busy}><Archive size={15} />归档</Button> : null}
                  {canEdit ? <Button onClick={() => void save()} disabled={busy}><Save size={15} />保存版本</Button> : null}
                </div>
              </div>
              {creating ? (
                <label className="block text-xs font-medium text-[var(--text-muted)]">分类<input value={category} onChange={(event) => setCategory(event.target.value)} className="mt-1.5 w-full border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-primary)]" /></label>
              ) : null}
              <textarea value={content} onChange={(event) => setContent(event.target.value)} readOnly={!canEdit} rows={22} className="w-full resize-y border border-[var(--border-soft)] bg-[var(--surface-2)] px-3 py-3 font-mono text-xs leading-6 text-[var(--text-primary)] read-only:opacity-75" />
              {canEdit && versions.length ? (
                <div className="border-t border-[var(--border-soft)] pt-4">
                  <div className="mb-2 flex items-center gap-2 text-sm font-medium"><History size={15} />版本记录</div>
                  <div className="divide-y divide-[var(--border-soft)]">
                    {versions.map((version) => (
                      <div key={version.version} className="flex items-center justify-between gap-3 py-2 text-sm">
                        <span>v{version.version}</span>
                        <Button size="sm" variant="ghost" disabled={busy || registry.some((item) => item.skill_name === selected && item.current_version === version.version)} onClick={() => void rollback(selected, version.version)} title="恢复此版本"><RotateCcw size={14} /></Button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="py-20 text-center text-sm text-[var(--text-muted)]">选择一个 Skill 查看内容与版本。</div>
          )}
        </Panel>
      </div>
    </div>
  );
}
