"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@aioj/ui";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark" | "loading">("loading");

  useEffect(() => {
    // Check initial theme class on the document Element
    if (document.documentElement.classList.contains("light")) {
      setTheme("light");
    } else {
      setTheme("dark");
    }
  }, []);

  const toggleTheme = () => {
    const isLight = document.documentElement.classList.contains("light");
    if (isLight) {
      document.documentElement.classList.remove("light");
      localStorage.setItem("syncode-theme", "dark");
      setTheme("dark");
    } else {
      document.documentElement.classList.add("light");
      localStorage.setItem("syncode-theme", "light");
      setTheme("light");
    }
  };

  return (
    <Button size="sm" variant="ghost" onClick={toggleTheme} aria-label="Toggle theme">
      {theme === "loading" ? (
        <span className="w-3.5 h-3.5 opacity-0 inline-block" />
      ) : theme === "light" ? (
        <Sun size={15} className="text-amber-500" />
      ) : (
        <Moon size={15} className="text-[var(--text-muted)]" />
      )}
    </Button>
  );
}
