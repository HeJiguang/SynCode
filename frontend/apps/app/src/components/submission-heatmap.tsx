import * as React from "react";

type HeatmapProps = {
  data: Record<string, number>;
  weeks?: number;
};

type HeatmapCell = {
  date: string;
  count: number;
  intensity: ReturnType<typeof getIntensity>;
};

type HeatmapColumn = {
  key: string;
  monthLabel: string;
  cells: HeatmapCell[];
};

function getIntensity(count: number): 0 | 1 | 2 | 3 | 4 {
  if (count === 0) return 0;
  if (count <= 1) return 1;
  if (count <= 3) return 2;
  if (count <= 5) return 3;
  return 4;
}

function formatDateKey(date: Date) {
  return date.toISOString().slice(0, 10);
}

function formatMonthLabel(date: Date) {
  return `${date.getMonth() + 1}月`;
}

const DAYS = ["一", "", "三", "", "五", "", ""];
const LEGEND_LEVELS = [0, 1, 2, 3, 4] as const;

export function SubmissionHeatmap({ data, weeks = 24 }: HeatmapProps) {
  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(today.getDate() - weeks * 7 + 1);

  const dayOfWeek = startDate.getDay();
  startDate.setDate(startDate.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));

  const cells: HeatmapCell[] = [];
  const cursor = new Date(startDate);
  while (cursor <= today) {
    const key = formatDateKey(cursor);
    const count = data[key] ?? 0;
    cells.push({ date: key, count, intensity: getIntensity(count) });
    cursor.setDate(cursor.getDate() + 1);
  }

  const columns: HeatmapColumn[] = [];
  let previousMonth = -1;
  for (let index = 0; index < cells.length; index += 7) {
    const columnCells = cells.slice(index, index + 7);
    const columnDate = new Date(startDate);
    columnDate.setDate(startDate.getDate() + index);

    const month = columnDate.getMonth();
    const monthLabel = index === 0 || month !== previousMonth ? formatMonthLabel(columnDate) : "";
    previousMonth = month;

    columns.push({
      key: formatDateKey(columnDate),
      monthLabel,
      cells: columnCells
    });
  }

  return (
    <div className="space-y-4 rounded-[20px] border border-[var(--border-soft)] bg-[var(--surface-1)]/72 px-4 py-4 md:px-5">
      <div className="grid gap-3 md:grid-cols-[2rem_minmax(0,1fr)] md:items-end">
        <div aria-hidden />
        <div className="overflow-x-auto">
          <div
            className="grid min-w-[520px] gap-x-1.5 md:min-w-0 md:gap-x-2"
            style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}
          >
            {columns.map((column) => (
              <div
                key={`month-${column.key}`}
                className="min-w-0 text-left text-[11px] leading-none text-[var(--text-muted)]"
              >
                {column.monthLabel}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-[2rem_minmax(0,1fr)]">
        <div className="grid grid-rows-7 gap-1.5 pt-[1px] text-[11px] leading-none text-[var(--text-muted)] md:gap-2">
          {DAYS.map((label, index) => (
            <div key={`${label}-${index}`} className="flex items-center">
              {label}
            </div>
          ))}
        </div>

        <div className="overflow-x-auto">
          <div
            className="grid min-w-[520px] gap-x-1.5 md:min-w-0 md:gap-x-2"
            style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}
          >
            {columns.map((column) => (
              <div key={column.key} className="grid justify-items-center gap-y-1.5 md:gap-y-2">
                {column.cells.map((cell) => (
                  <div
                    key={cell.date}
                    aria-label={`${cell.date}: ${cell.count} 次提交`}
                    title={`${cell.date}: ${cell.count} 次提交`}
                    data-intensity={cell.intensity}
                    className="submission-heatmap-cell h-[10px] w-[10px] rounded-[3px] transition-transform duration-150 ease-out hover:-translate-y-px md:h-[11px] md:w-[11px]"
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 text-[11px] text-[var(--text-muted)]">
        <span>少</span>
        {LEGEND_LEVELS.map((level) => (
          <div
            key={level}
            data-intensity={level}
            className="submission-heatmap-cell h-[10px] w-[10px] rounded-[3px] md:h-[11px] md:w-[11px]"
          />
        ))}
        <span>多</span>
      </div>
    </div>
  );
}
