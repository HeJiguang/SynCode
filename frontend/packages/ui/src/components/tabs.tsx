"use client";

import * as React from "react";
import { useState } from "react";

type TabsProps = {
  tabs: {
    id: string;
    label: React.ReactNode;
    content: React.ReactNode;
  }[];
  defaultTab?: string;
  className?: string;
};

export function Tabs({ tabs, defaultTab, className = "" }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab ?? tabs[0]?.id);

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Tab List */}
      <div className="flex items-center gap-6 border-b border-[var(--border-soft)] px-5">
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              className={`relative py-3.5 text-sm font-semibold transition-colors
                ${isActive ? "text-[var(--text-primary)]" : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"}
              `}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
              {isActive && (
                <div className="absolute bottom-0 left-0 w-full h-0.5 bg-[var(--text-primary)]" />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-auto">
        {tabs.find((t) => t.id === activeTab)?.content}
      </div>
    </div>
  );
}
