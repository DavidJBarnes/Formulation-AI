import { useMemo } from 'react'
import { cn } from '@/lib/utils'

export interface ScatterPoint {
  project: string
  iteration: number
  objective: number
}

interface ScatterChartProps {
  points: ScatterPoint[]
  className?: string
}

const SERIES_COLORS = [
  'hsl(221 83% 50%)',
  'hsl(262 70% 55%)',
  'hsl(159 64% 42%)',
  'hsl(15 85% 55%)',
  'hsl(43 85% 50%)',
  'hsl(199 89% 48%)',
]

export function ScatterChart({ points, className }: ScatterChartProps) {
  const { byProject, projectColors, maxIter } = useMemo(() => {
    const map: Record<string, ScatterPoint[]> = {}
    for (const p of points) (map[p.project] ??= []).push(p)
    const colors: Record<string, string> = {}
    Object.keys(map).forEach((name, i) => {
      colors[name] = SERIES_COLORS[i % SERIES_COLORS.length]
    })
    const maxI = Math.max(1, ...points.map((p) => p.iteration))
    return { byProject: map, projectColors: colors, maxIter: maxI }
  }, [points])

  const width = 760
  const height = 320
  const padL = 50
  const padR = 14
  const padT = 16
  const padB = 38
  const xFor = (i: number) => padL + ((i - 1) / (maxIter - 1 || 1)) * (width - padL - padR)
  const yFor = (o: number) => padT + (1 - o) * (height - padT - padB)

  const yTicks = [0, 0.25, 0.5, 0.75, 1]
  const xTicks = Array.from({ length: maxIter }, (_, i) => i + 1)

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
        {/* y gridlines */}
        {yTicks.map((y) => (
          <g key={y}>
            <line
              x1={padL}
              x2={width - padR}
              y1={yFor(y)}
              y2={yFor(y)}
              className="stroke-border"
              strokeDasharray={y === 1 ? '0' : '2 3'}
            />
            <text
              x={padL - 8}
              y={yFor(y) + 3}
              textAnchor="end"
              className="fill-muted-foreground text-[10px]"
            >
              {Math.round(y * 100)}%
            </text>
          </g>
        ))}
        {/* x ticks */}
        {xTicks.map((x) => (
          <g key={x}>
            <line
              x1={xFor(x)}
              x2={xFor(x)}
              y1={padT}
              y2={height - padB}
              className="stroke-border/60"
              strokeDasharray="1 4"
            />
            <text
              x={xFor(x)}
              y={height - padB + 14}
              textAnchor="middle"
              className="fill-muted-foreground text-[10px]"
            >
              I{x}
            </text>
          </g>
        ))}
        {/* x label */}
        <text
          x={(width - padR + padL) / 2}
          y={height - 6}
          textAnchor="middle"
          className="fill-muted-foreground text-[10px] font-medium uppercase tracking-wider"
        >
          Iteration
        </text>
        {/* y label */}
        <text
          x={-(padT + (height - padT - padB) / 2)}
          y={14}
          transform="rotate(-90)"
          textAnchor="middle"
          className="fill-muted-foreground text-[10px] font-medium uppercase tracking-wider"
        >
          Objective progress
        </text>

        {/* Trajectory lines per project */}
        {Object.entries(byProject).map(([name, pts]) => {
          const sorted = [...pts].sort((a, b) => a.iteration - b.iteration)
          const path = sorted
            .map((p, i) => `${i === 0 ? 'M' : 'L'}${xFor(p.iteration)},${yFor(p.objective)}`)
            .join(' ')
          return (
            <path
              key={name}
              d={path}
              fill="none"
              stroke={projectColors[name]}
              strokeWidth={1.5}
              strokeOpacity={0.45}
            />
          )
        })}
        {/* Points */}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={xFor(p.iteration)}
            cy={yFor(p.objective)}
            r={5}
            fill={projectColors[p.project]}
            fillOpacity={0.85}
            stroke="white"
            strokeWidth={1.5}
          />
        ))}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 px-2">
        {Object.entries(projectColors).map(([name, color]) => (
          <div key={name} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
            {name}
          </div>
        ))}
      </div>
    </div>
  )
}
