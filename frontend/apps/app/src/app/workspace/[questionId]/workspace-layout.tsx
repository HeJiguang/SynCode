"use client";

import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, ChevronLeft, ChevronRight } from "lucide-react";

const AI_MIN_WIDTH = 260;
const AI_MAX_WIDTH = 560;
const AI_DEFAULT_WIDTH = 340;
const AI_COLLAPSED_WIDTH = 48;
const PROBLEM_MIN_WIDTH = 320;
const PROBLEM_MAX_WIDTH = 620;
const PROBLEM_DEFAULT_WIDTH = 420;
const AI_STORAGE_KEY = "syncode_ai_panel_width";
const PROBLEM_STORAGE_KEY = "syncode_problem_panel_width";

type DragTarget = "problem" | "ai" | null;

type WorkspaceLayoutProps = {
  aiPanel: React.ReactNode;
  questionPanel: React.ReactNode;
  editorPanel: React.ReactNode;
};

export function WorkspaceLayout({ aiPanel, questionPanel, editorPanel }: WorkspaceLayoutProps) {
  const [aiExpanded, setAiExpanded] = useState(true);
  const [problemWidth, setProblemWidth] = useState<number>(() => {
    if (typeof window === "undefined") return PROBLEM_DEFAULT_WIDTH;
    const saved = localStorage.getItem(PROBLEM_STORAGE_KEY);
    const parsed = saved ? Number(saved) : NaN;
    return Number.isFinite(parsed) && parsed >= PROBLEM_MIN_WIDTH && parsed <= PROBLEM_MAX_WIDTH
      ? parsed
      : PROBLEM_DEFAULT_WIDTH;
  });
  const [aiWidth, setAiWidth] = useState<number>(() => {
    if (typeof window === "undefined") return AI_DEFAULT_WIDTH;
    const saved = localStorage.getItem(AI_STORAGE_KEY);
    const parsed = saved ? Number(saved) : NaN;
    return Number.isFinite(parsed) && parsed >= AI_MIN_WIDTH && parsed <= AI_MAX_WIDTH
      ? parsed
      : AI_DEFAULT_WIDTH;
  });

  const dragTargetRef = useRef<DragTarget>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const startDragging = useCallback(
    (target: DragTarget, width: number, clientX: number) => {
      dragTargetRef.current = target;
      startXRef.current = clientX;
      startWidthRef.current = width;

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    []
  );

  const handleProblemDragStart = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault();
      startDragging("problem", problemWidth, event.clientX);
    },
    [problemWidth, startDragging]
  );

  const handleAiDragStart = useCallback(
    (event: React.MouseEvent) => {
      if (!aiExpanded) return;
      event.preventDefault();
      startDragging("ai", aiWidth, event.clientX);
    },
    [aiExpanded, aiWidth, startDragging]
  );

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      if (!dragTargetRef.current) return;

      if (dragTargetRef.current === "problem") {
        const delta = event.clientX - startXRef.current;
        const nextWidth = Math.min(PROBLEM_MAX_WIDTH, Math.max(PROBLEM_MIN_WIDTH, startWidthRef.current + delta));
        setProblemWidth(nextWidth);
        return;
      }

      const delta = startXRef.current - event.clientX;
      const nextWidth = Math.min(AI_MAX_WIDTH, Math.max(AI_MIN_WIDTH, startWidthRef.current + delta));
      setAiWidth(nextWidth);
    };

    const handleMouseUp = () => {
      if (!dragTargetRef.current) return;
      const finishedTarget = dragTargetRef.current;
      dragTargetRef.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";

      if (finishedTarget === "problem") {
        setProblemWidth((width) => {
          localStorage.setItem(PROBLEM_STORAGE_KEY, String(width));
          return width;
        });
        return;
      }

      setAiWidth((width) => {
        localStorage.setItem(AI_STORAGE_KEY, String(width));
        return width;
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
    <div ref={containerRef} className="syncode-workspace-scene h-full w-full p-3">
      <div className="syncode-workspace-shell flex h-full w-full overflow-hidden">
        <div className="flex min-w-0 flex-1">
          <section
            className="syncode-workspace-problem syncode-workspace-column h-full min-w-0 shrink-0"
            style={{ width: problemWidth }}
          >
            {questionPanel}
          </section>

          <div
            className="syncode-workspace-divider syncode-workspace-primary-resize-handle group relative cursor-col-resize"
            onMouseDown={handleProblemDragStart}
            title="拖动调整题目区宽度"
          >
            <div className="syncode-workspace-resize-pill" />
          </div>

          <section className="syncode-workspace-editor syncode-workspace-column h-full min-w-0 flex-1">
            {editorPanel}
          </section>
        </div>

        <div className="syncode-workspace-divider" />

        <aside
          className="syncode-workspace-ai relative flex shrink-0"
          style={{
            width: currentWidth,
            transition: dragTargetRef.current ? "none" : "width 0.3s cubic-bezier(0.16,1,0.3,1)"
          }}
        >
          {aiExpanded ? (
            <div className="h-full w-full pl-[6px]">{aiPanel}</div>
          ) : (
            <div className="absolute inset-0 bg-[var(--surface-1)]" />
          )}

          {aiExpanded && (
            <div
              onMouseDown={handleAiDragStart}
              className="group absolute left-0 top-0 z-20 flex h-full w-[8px] cursor-col-resize items-center justify-center"
              title="拖动调整宽度"
            >
              <div className="syncode-workspace-resize-pill" />
            </div>
          )}

          <button
            onClick={() => setAiExpanded((expanded) => !expanded)}
            className="absolute -left-3 top-1/2 z-10 flex h-12 w-6 -translate-y-1/2 items-center justify-center rounded-[8px] border border-[var(--border-strong)] bg-[var(--surface-1)] text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text-primary)]"
          >
            {aiExpanded ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
          </button>

          {!aiExpanded && (
            <div className="absolute inset-0 z-10 flex cursor-pointer flex-col items-center justify-start pt-6" onClick={() => setAiExpanded(true)}>
              <Bot size={17} className="mb-12 text-[var(--accent)]" />
              <div className="-rotate-90 whitespace-nowrap text-[10px] font-semibold tracking-[0.18em] text-[var(--text-muted)]">
                提问
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
