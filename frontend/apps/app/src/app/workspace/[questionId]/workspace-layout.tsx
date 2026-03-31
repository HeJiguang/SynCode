"use client";

import * as React from "react";
import { useState, useRef, useCallback, useEffect } from "react";
import { ChevronLeft, ChevronRight, Bot } from "lucide-react";

const AI_MIN_WIDTH = 260;
const AI_MAX_WIDTH = 560;
const AI_DEFAULT_WIDTH = 340;
const AI_COLLAPSED_WIDTH = 48;
const LOCAL_STORAGE_KEY = "syncode_ai_panel_width";

type WorkspaceLayoutProps = {
  aiPanel: React.ReactNode;
  questionPanel: React.ReactNode;
  editorPanel: React.ReactNode;
};

export function WorkspaceLayout({ aiPanel, questionPanel, editorPanel }: WorkspaceLayoutProps) {
  const [aiExpanded, setAiExpanded] = useState(true);
  const [aiWidth, setAiWidth] = useState<number>(() => {
    if (typeof window === "undefined") return AI_DEFAULT_WIDTH;
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    const parsed = saved ? Number(saved) : NaN;
    return Number.isFinite(parsed) && parsed >= AI_MIN_WIDTH && parsed <= AI_MAX_WIDTH
      ? parsed
      : AI_DEFAULT_WIDTH;
  });

  const isDraggingRef = useRef(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleDragStart = useCallback(
    (e: React.MouseEvent) => {
      if (!aiExpanded) return;
      e.preventDefault();
      isDraggingRef.current = true;
      startXRef.current = e.clientX;
      startWidthRef.current = aiWidth;

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [aiExpanded, aiWidth]
  );

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      // dragging left = making AI panel wider (delta is negative when moving left)
      const delta = startXRef.current - e.clientX;
      const nextWidth = Math.min(AI_MAX_WIDTH, Math.max(AI_MIN_WIDTH, startWidthRef.current + delta));
      setAiWidth(nextWidth);
    };

    const handleMouseUp = () => {
      if (!isDraggingRef.current) return;
      isDraggingRef.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      // persist
      setAiWidth((w) => {
        localStorage.setItem(LOCAL_STORAGE_KEY, String(w));
        return w;
      });
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const currentWidth = aiExpanded ? aiWidth : AI_COLLAPSED_WIDTH;

  return (
    <div ref={containerRef} className="flex h-full w-full gap-3 p-3 bg-[var(--bg)]">
      {/* ── Main Workspace ── */}
      <div className="flex flex-1 gap-3 min-w-0">
        {/* Question & Result (Left) */}
        <div className="w-[45%] lg:w-1/2 min-w-0 h-full">
          {questionPanel}
        </div>
        {/* Editor (Center) */}
        <div className="flex-1 min-w-0 h-full">
          {editorPanel}
        </div>
      </div>

      {/* ── AI Sidebar (Rightmost) ── */}
      <div
        className="relative flex shrink-0"
        style={{
          width: currentWidth,
          transition: isDraggingRef.current ? "none" : "width 0.3s cubic-bezier(0.16,1,0.3,1)"
        }}
      >
        {/* Drag Handle — only when expanded */}
        {aiExpanded && (
          <div
            onMouseDown={handleDragStart}
            className="absolute left-0 top-0 h-full w-[6px] z-20 cursor-col-resize group flex items-center justify-center"
            title="拖动以调整 AI 面板宽度"
          >
            {/* Visual indicator strip */}
            <div className="h-12 w-[3px] rounded-full bg-[var(--border-soft)] group-hover:bg-[var(--accent)] transition-colors duration-150" />
          </div>
        )}

        {/* Panel content */}
        <div
          className={`w-full h-full transform origin-right transition-all duration-300 ${
            aiExpanded ? "opacity-100 scale-100 pl-[6px]" : "opacity-0 scale-95 pointer-events-none"
          } ${!aiExpanded ? "" : ""}`}
        >
          {aiPanel}
        </div>

        {/* Collapsed state background */}
        {!aiExpanded && (
          <div className="absolute inset-0 bg-[var(--surface-1)] rounded-[var(--radius-card)] border border-[var(--border-soft)]" />
        )}

        {/* Toggle Button */}
        <button
          onClick={() => setAiExpanded(!aiExpanded)}
          className="absolute -left-3 top-1/2 -translate-y-1/2 z-10 flex h-16 w-4 items-center justify-center rounded-full border border-[var(--border-strong)] bg-[var(--surface-1)] text-[var(--text-muted)] shadow-sm hover:text-[var(--text-primary)] hover:bg-[var(--surface-2)] transition-colors"
        >
          {aiExpanded ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        </button>

        {/* Collapsed Vertical Text */}
        {!aiExpanded && (
          <div
            className="absolute inset-0 flex flex-col items-center justify-start pt-6 cursor-pointer z-10"
            onClick={() => setAiExpanded(true)}
          >
            <Bot size={18} className="text-[var(--accent)] mb-14" />
            <div className="-rotate-90 text-[11px] font-bold tracking-[0.2em] text-[var(--text-muted)] uppercase whitespace-nowrap">
              AI Assistant
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
