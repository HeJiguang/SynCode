import * as React from "react";

type HeatmapProps = {
  data: Record<string, number>;
  weeks?: number;
};

function getIntensity(count: number): 0 | 1 | 2 | 3 | 4 {
  if (count === 0) return 0;
  if (count <= 1) return 1;
  if (count <= 3) return 2;
  if (count <= 5) return 3;
  return 4;
}

const intensityClasses: Record<0 | 1 | 2 | 3 | 4, string> = {
  0: "bg-[var(--surface-2)]",
  1: "bg-[var(--accent)]/18",
  2: "bg-[var(--accent)]/36",
  3: "bg-[var(--accent)]/64",
  4: "bg-[var(--accent)]"
};

const DAYS = ["", "一", "", "三", "", "五", ""];

export function SubmissionHeatmap({ data, weeks = 24 }: HeatmapProps) {
  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(today.getDate() - weeks * 7 + 1);

  const dayOfWeek = startDate.getDay();
  startDate.setDate(startDate.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));

  const cells: { date: string; count: number; intensity: ReturnType<typeof getIntensity> }[] = [];
  const cursor = new Date(startDate);
  while (cursor <= today) {
    const key = cursor.toISOString().slice(0, 10);
    const count = data[key] ?? 0;
    cells.push({ date: key, count, intensity: getIntensity(count) });
    cursor.setDate(cursor.getDate() + 1);
  }

  const columns: typeof cells[] = [];
  for (let index = 0; index < cells.length; index += 7) {
    columns.push(cells.slice(index, index + 7));
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-1">
        <div className="flex shrink-0 flex-col gap-[3px] pr-1">
          {DAYS.map((label, index) => (
            <div
              key={`${label}-${index}`}
              className="flex h-[10px] w-3 items-center text-[9px] leading-none text-[var(--text-muted)]"
            >
              {label}
            </div>
          ))}
        </div>

        <div className="flex gap-[3px] overflow-hidden">
          {columns.map((column, columnIndex) => (
            <div key={columnIndex} className="flex flex-col gap-[3px]">
              {column.map((cell) => (
                <div
                  key={cell.date}
                  title={`${cell.date}: ${cell.count} 次提交`}
                  className={`h-[10px] w-[10px] cursor-default rounded-[2px] transition-opacity duration-300 ease-out hover:opacity-75 ${intensityClasses[cell.intensity]}`}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-end gap-2">
        <span className="text-[10px] text-[var(--text-muted)]">少</span>
        {([0, 1, 2, 3, 4] as const).map((level) => (
          <div key={level} className={`h-[10px] w-[10px] rounded-[2px] ${intensityClasses[level]}`} />
        ))}
        <span className="text-[10px] text-[var(--text-muted)]">多</span>
      </div>
    </div>
  );
}
