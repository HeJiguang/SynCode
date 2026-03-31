"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { Button } from "@aioj/ui";
import { adminApiPath } from "../lib/paths";

type AdminUserStatusToggleProps = {
  userId: string;
  status: "正常" | "冻结";
};

export function AdminUserStatusToggle({ userId, status }: AdminUserStatusToggleProps) {
  const router = useRouter();
  const [loading, setLoading] = React.useState(false);
  const nextStatus = status === "正常" ? 1 : 0;

  async function handleClick() {
    setLoading(true);
    try {
      await fetch(adminApiPath("/users/status"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: Number(userId), status: nextStatus })
      });
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button type="button" variant="ghost" size="sm" disabled={loading} onClick={handleClick}>
      {status === "正常" ? "冻结" : "恢复"}
    </Button>
  );
}
