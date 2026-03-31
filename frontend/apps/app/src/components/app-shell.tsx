import * as React from "react";
import type { ReactNode } from "react";
import { BellDot, LogIn, Settings } from "lucide-react";

import { appNav, productTagline } from "@aioj/config";
import { Button } from "@aioj/ui";
import { appPublicPath } from "../lib/paths";
import { ThemeToggle } from "./theme-toggle";

type AppShellProps = {
  title?: string;
  description?: string;
  actions?: ReactNode;
  eyebrow?: string;
  children: ReactNode;
  rail?: ReactNode;
  immersive?: boolean;
  demoMode?: boolean;
};

export function AppShell({ children, rail, immersive, demoMode = false }: AppShellProps) {
  const hasRail = Boolean(rail);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-[var(--border-soft)] bg-[var(--bg)]/80 backdrop-blur-md">
        <div className={`mx-auto flex h-14 items-center justify-between px-6 ${immersive ? "w-full" : "max-w-[1720px]"}`}>
          <a className="flex items-center gap-3 transition-opacity hover:opacity-80" href={appPublicPath("/")}>
            <div className="flex h-7 w-7 items-center justify-center rounded-[4px] bg-[var(--text-primary)] text-[var(--bg)] text-xs font-bold tracking-tight shadow-[var(--shadow-panel)]">
              SC
            </div>
            <div>
              <p className="text-[13px] font-semibold leading-tight tracking-wide text-[var(--text-primary)]">SynCode</p>
              <p className="mt-0.5 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
                {productTagline}
              </p>
            </div>
          </a>

          <div className="flex items-center gap-2">
            <a href={`${appPublicPath("/")}#announcements`}>
              <Button size="sm" variant="ghost">
                <BellDot size={14} className="text-[var(--text-muted)]" />
                <span className="ml-0.5">鍏憡</span>
              </Button>
            </a>
            <a href={appPublicPath("/settings")}>
              <Button size="sm" variant="ghost">
                <Settings size={14} className="text-[var(--text-muted)]" />
                <span className="ml-0.5">涓汉璁剧疆</span>
              </Button>
            </a>
            {demoMode ? (
              <a href={appPublicPath("/login")}>
                <Button size="sm" variant="secondary" className="font-medium">
                  <LogIn size={14} className="text-[var(--text-secondary)]" />
                  <span className="ml-1">鐧诲綍</span>
                </Button>
              </a>
            ) : null}
            <ThemeToggle />
          </div>
        </div>
      </header>

      {demoMode ? (
        <div className="border-b border-[var(--border-soft)] bg-[var(--surface-2)]/80 backdrop-blur-md">
          <div className={`mx-auto flex items-center justify-between gap-4 px-6 py-3 ${immersive ? "w-full" : "max-w-[1720px]"}`}>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              褰撳墠鏈櫥褰曪紝姝ｅ湪灞曠ず鍏紑鍐呭涓庢紨绀烘暟鎹€傜櫥褰曞悗鍙娇鐢ㄧ湡瀹為鐩鎯呫€佺郴缁熷叕鍛娿€佽缁冭鍒掋€佸垽棰樻彁浜ゃ€乄ebSocket 瀹炴椂缁撴灉鍜?AI 娴佸紡鑳藉姏銆?
            </p>
            <a href={appPublicPath("/login")} className="shrink-0">
              <Button size="sm">绔嬪嵆鐧诲綍</Button>
            </a>
          </div>
        </div>
      ) : null}

      <div className={`mx-auto flex ${immersive ? "w-full" : "max-w-[1720px]"}`}>
        {!immersive ? (
          <aside className="hidden w-[260px] shrink-0 border-r border-[var(--border-soft)] xl:block">
            <div className="sticky top-14 p-4">
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">
                Menu
              </p>
              <nav className="space-y-[2px]">
                {appNav.map((item) => (
                  <a
                    key={item.label}
                    className="group flex items-center rounded-[var(--radius-sm)] px-3 py-2 text-sm font-medium text-[var(--text-secondary)] transition-all duration-200 hover:bg-[var(--surface-2)] hover:text-[var(--text-primary)]"
                    href={appPublicPath(item.href)}
                  >
                    {item.label}
                  </a>
                ))}
              </nav>
            </div>
          </aside>
        ) : null}

        <main className={`min-w-0 flex-1 ${hasRail && !immersive ? "grid xl:grid-cols-[minmax(0,1fr)_340px]" : ""}`}>
          <div className={immersive ? "h-[calc(100vh-56px)]" : "space-y-8 p-8 md:p-10 xl:pr-10"}>{children}</div>

          {!immersive && hasRail ? (
            <aside className="hidden border-l border-[var(--border-soft)] xl:block">
              <div className="space-y-6 p-6">{rail}</div>
            </aside>
          ) : null}
        </main>
      </div>
    </div>
  );
}
