import { useMemo } from 'react'
import type { PortfolioProject } from '@/data/types'
import { cn } from '@/lib/utils'

interface GanttChartProps {
  projects: PortfolioProject[]
  className?: string
}

const STATUS_FILL: Record<PortfolioProject['status'], string> = {
  iterating: 'fill-brand/80',
  converged: 'fill-emerald-500/80',
  flagged: 'fill-amber-500/85',
  planning: 'fill-slate-400/70',
}

const STATUS_STROKE: Record<PortfolioProject['status'], string> = {
  iterating: 'stroke-brand',
  converged: 'stroke-emerald-600',
  flagged: 'stroke-amber-600',
  planning: 'stroke-slate-500',
}

export function GanttChart({ projects, className }: GanttChartProps) {
  const { domainStart, domainEnd, monthTicks } = useMemo(() => {
    const dates = projects.flatMap((p) => [new Date(p.startedAt), new Date(p.endsAt)])
    const minMs = Math.min(...dates.map((d) => d.getTime()))
    const maxMs = Math.max(...dates.map((d) => d.getTime()))
    const start = new Date(minMs)
    start.setDate(1)
    const end = new Date(maxMs)
    end.setMonth(end.getMonth() + 1, 1)
    const ticks: Date[] = []
    const cursor = new Date(start)
    while (cursor <= end) {
      ticks.push(new Date(cursor))
      cursor.setMonth(cursor.getMonth() + 1)
    }
    return { domainStart: start, domainEnd: end, monthTicks: ticks }
  }, [projects])

  const width = 760
  const rowHeight = 28
  const labelWidth = 200
  const chartWidth = width - labelWidth - 16
  const height = projects.length * rowHeight + 32
  const today = new Date('2026-04-24').getTime()

  const xFor = (d: Date) => {
    const t = (d.getTime() - domainStart.getTime()) / (domainEnd.getTime() - domainStart.getTime())
    return labelWidth + t * chartWidth
  }

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={cn('w-full', className)} role="img">
      {/* Month gridlines */}
      {monthTicks.map((m, i) => (
        <g key={i}>
          <line
            x1={xFor(m)}
            x2={xFor(m)}
            y1={20}
            y2={height - 4}
            className="stroke-border"
            strokeDasharray={i % 3 === 0 ? '0' : '2 3'}
          />
          {i % 2 === 0 && (
            <text
              x={xFor(m)}
              y={14}
              className="fill-muted-foreground text-[9px]"
              textAnchor="middle"
            >
              {m.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })}
            </text>
          )}
        </g>
      ))}

      {/* Today marker */}
      <line
        x1={xFor(new Date(today))}
        x2={xFor(new Date(today))}
        y1={20}
        y2={height - 4}
        className="stroke-brand"
        strokeWidth={1.5}
        strokeDasharray="4 3"
      />
      <text
        x={xFor(new Date(today))}
        y={height - 8}
        className="fill-brand text-[9px] font-medium"
        textAnchor="middle"
      >
        today
      </text>

      {/* Rows */}
      {projects.map((p, i) => {
        const y = 24 + i * rowHeight
        const x1 = xFor(new Date(p.startedAt))
        const x2 = xFor(new Date(p.endsAt))
        const progress = p.iteration / p.maxIterations
        return (
          <g key={p.id}>
            {/* Project label */}
            <text x={8} y={y + rowHeight / 2 + 4} className="fill-foreground text-[11px] font-medium">
              {p.name.length > 28 ? p.name.slice(0, 27) + '…' : p.name}
            </text>
            {/* Bar background */}
            <rect
              x={x1}
              y={y + 4}
              width={Math.max(2, x2 - x1)}
              height={rowHeight - 12}
              rx={4}
              className={cn(STATUS_FILL[p.status], 'opacity-30')}
            />
            {/* Progress fill */}
            <rect
              x={x1}
              y={y + 4}
              width={Math.max(2, (x2 - x1) * progress)}
              height={rowHeight - 12}
              rx={4}
              className={cn(STATUS_FILL[p.status])}
            />
            {/* Border */}
            <rect
              x={x1}
              y={y + 4}
              width={Math.max(2, x2 - x1)}
              height={rowHeight - 12}
              rx={4}
              fill="none"
              className={cn(STATUS_STROKE[p.status])}
              strokeWidth={1}
            />
            {/* Iteration label inside bar */}
            <text
              x={x1 + 6}
              y={y + rowHeight / 2 + 3.5}
              className="fill-white text-[9px] font-semibold"
            >
              {p.iteration > 0 ? `I${p.iteration}/${p.maxIterations}` : 'plan'}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
