import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "SynCode App",
  description: "SynCode 用户端演示，聚焦刷题、训练、考试和 AI 辅助工作流。"
};

/**
 * 在 <html> 上注入主题 class，避免 FOUC。
 * 读取 localStorage("theme") 或 prefers-color-scheme 系统偏好。
 */
const themeScript = `
(function() {
  var stored = localStorage.getItem('syncode-theme');
  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (stored === 'dark' || (!stored && prefersDark)) {
    document.documentElement.classList.remove('light');
  } else {
    document.documentElement.classList.add('light');
  }
})();
`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        {/* 主题注入脚本，阻塞渲染防止闪烁 */}
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
