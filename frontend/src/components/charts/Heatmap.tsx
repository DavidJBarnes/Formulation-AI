import { cn } from '@/lib/utils'

interface HeatmapProps {
  rows: string[]
  cols: string[]
  values: number[][] // [row][col], 0..1
  className?: string
}

function colorFor(v: number) {
  // 0 → soft red, 0.5 → amber, 1 → emerald — interpolate hue
  const clamped = Math.max(0, Math.min(1, v))
  const hue = 0 + clamped * 145 // 0 red → 145 emerald
  const sat = 70
  const light = 92 - clamped * 32 // lighter for low values, deeper for high
  return `hsl(${hue} ${sat}% ${light}%)`
}

function textColorFor(v: number) {
  return v > 0.55 ? 'white' : 'hsl(222 47% 18%)'
}

export function Heatmap({ rows, cols, values, className }: HeatmapProps) {
  const cellW = 96
  const cellH = 40
  const labelW = 170
  const headerH = 32
  const width = labelW + cols.length * cellW + 8
  const height = headerH + rows.length * cellH + 32

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={cn('w-full', className)}>
      {/* Column headers */}
      {cols.map((c, j) => (
        <text
          key={c}
          x={labelW + j * cellW + cellW / 2}
          y={headerH - 12}
          textAnchor="middle"
          className="fill-muted-foreground text-[10px] font-semibold uppercase tracking-wider"
        >
          {c}
        </text>
      ))}
      {/* Cells */}
      {rows.map((r, i) => (
        <g key={r}>
          <text
            x={labelW - 10}
            y={headerH + i * cellH + cellH / 2 + 4}
            textAnchor="end"
            className="fill-foreground text-[11px] font-medium"
          >
            {r}
          </text>
          {cols.map((_, j) => {
            const v = values[i][j]
            return (
              <g key={j}>
                <rect
                  x={labelW + j * cellW + 3}
                  y={headerH + i * cellH + 3}
                  width={cellW - 6}
                  height={cellH - 6}
                  rx={5}
                  fill={colorFor(v)}
                  stroke="hsl(214 32% 91%)"
                  strokeWidth={0.5}
                />
                <text
                  x={labelW + j * cellW + cellW / 2}
                  y={headerH + i * cellH + cellH / 2 + 4}
                  textAnchor="middle"
                  fill={textColorFor(v)}
                  className="text-[11px] font-semibold tabular-nums"
                >
                  {Math.round(v * 100)}%
                </text>
              </g>
            )
          })}
        </g>
      ))}
      {/* Legend */}
      <g transform={`translate(${labelW}, ${height - 16})`}>
        <text x={0} y={0} className="fill-muted-foreground text-[10px] font-medium uppercase tracking-wider">
          % of target met
        </text>
        {[0, 0.25, 0.5, 0.75, 1].map((v, i) => (
          <g key={v} transform={`translate(${110 + i * 60}, -10)`}>
            <rect width={50} height={10} rx={2} fill={colorFor(v)} />
            <text x={25} y={20} textAnchor="middle" className="fill-muted-foreground text-[9px]">
              {Math.round(v * 100)}%
            </text>
          </g>
        ))}
      </g>
    </svg>
  )
}
