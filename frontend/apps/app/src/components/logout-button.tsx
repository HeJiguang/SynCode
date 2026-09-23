"use client";

import * as React from "react";
import { LogOut } from "lucide-react";

import { clearBrowserAccessToken } from "@aioj/api";
import { Button } from "@aioj/ui";
import { appApiPath, appPublicPath } from "../lib/paths";

export function LogoutButton({ demoMode = false }: { demoMode?: boolean }) {
  const [loading, setLoading] = React.useState(false);
  const label = demoMode ? "退出体验" : "退出登录";

  async function logout() {
    setLoading(true);

    try {
      await fetch(appApiPath("/auth/logout"), { method: "POST" });
    } finally {
      clearBrowserAccessToken();
      window.location.assign(appPublicPath("/login"));
    }
  }

  return (
    <Button size="sm" variant="ghost" disabled={loading} onClick={() => void logout()} aria-label={label} title={label}>
      <LogOut size={14} className="text-[var(--text-muted)]" />
      <span className="hidden sm:inline">{loading ? "正在退出..." : label}</span>
    </Button>
  );
}
