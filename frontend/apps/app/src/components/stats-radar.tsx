import * as React from "react";

type RadarDimension = {
  label: string;
  value: number; // 0-100
};

type StatsRadarProps = {
  dimensions: RadarDimension[];
  size?: number;
};

/**
 * StatsRadar — 纯 SVG 六边形能力雷达图
 * 零依赖，无 ECharts，完全融合设计系统。
 */
export function StatsRadar({ dimensions, size = 220 }: StatsRadarProps) {
  const n = dimensions.length;
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size / 2 - 36; // 留出 label 空间

  // 将索引 i 映射到角度（从顶部顺时针，-90度偏移）
  function angle(i: number) {
    return (Math.PI * 2 * i) / n - Math.PI / 2;
  }

  function point(r: number, i: number) {
    const a = angle(i);
    return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  }

  function toPath(pts: { x: number; y: number }[]) {
    return pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" ") + " Z";
  }

  // 背景刻度环 (20/40/60/80/100)
  const rings = [0.2, 0.4, 0.6, 0.8, 1.0];

  // 数据多边形
  const dataPoints = dimensions.map((d, i) => point((d.value / 100) * maxR, i));

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} className="overflow-visible">
      {/* ── 背景环 ── */}
      {rings.map((r, ri) => {
        const pts = Array.from({ length: n }, (_, i) => point(r * maxR, i));
        return (
          <path
            key={ri}
            d={toPath(pts)}
            fill="none"
            stroke="var(--border-soft)"
            strokeWidth={ri === rings.length - 1 ? 1.5 : 1}
          />
        );
      })}

      {/* ── 轴线 ── */}
      {dimensions.map((_, i) => {
        const outer = point(maxR, i);
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={outer.x}
            y2={outer.y}
            stroke="var(--border-soft)"
            strokeWidth={1}
          />
        );
      })}

      {/* ── 数据面积 ── */}
      <path
        d={toPath(dataPoints)}
        fill="var(--accent)"
        fillOpacity={0.15}
        stroke="var(--accent)"
        strokeWidth={2}
        strokeLinejoin="round"
      />

      {/* ── 数据点 ── */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={4} fill="var(--accent)" />
      ))}

      {/* ── 标签 ── */}
      {dimensions.map((d, i) => {
        const labelR = maxR + 22;
        const p = point(labelR, i);
        const anchor =
          Math.abs(p.x - cx) < 4 ? "middle" : p.x < cx ? "end" : "start";
        return (
          <text
            key={i}
            x={p.x}
            y={p.y}
            textAnchor={anchor}
            dominantBaseline="middle"
            fontSize={10}
            fontWeight={600}
            fill="var(--text-muted)"
            fontFamily="var(--font-sans)"
            letterSpacing="0.04em"
          >
            {d.label}
          </text>
        );
      })}

      {/* ── 数值标注 ── */}
      {dataPoints.map((p, i) => {
        const v = dimensions[i]?.value ?? 0;
        if (v === 0) return null;
        const offset = point((dimensions[i].value / 100) * maxR - 12, i);
        return (
          <text
            key={`val-${i}`}
            x={offset.x}
            y={offset.y}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={9}
            fontWeight={700}
            fill="var(--accent)"
            fontFamily="var(--font-mono)"
          >
            {v}
          </text>
        );
      })}
    </svg>
  );
}
