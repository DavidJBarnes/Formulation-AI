import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, FlaskConical, Sparkles, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { GanttChart } from '@/components/charts/GanttChart'
import { ScatterChart } from '@/components/charts/ScatterChart'
import { Heatmap } from '@/components/charts/Heatmap'
import { StatusBadge } from '@/components/StatusBadge'
import {
  heatmapCols,
  heatmapRows,
  heatmapValues,
  portfolioProjects,
  portfolioScatter,
} from '@/data/fixtures'

export function PortfolioPage() {
  const stats = useMemo(() => {
    const total = portfolioProjects.length
    const iterating = portfolioProjects.filter((p) => p.status === 'iterating').length
    const converged = portfolioProjects.filter((p) => p.status === 'converged').length
    const flagged = portfolioProjects.filter((p) => p.status === 'flagged').length
    const totalIters = portfolioProjects.reduce((s, p) => s + p.iteration, 0)
    return { total, iterating, converged, flagged, totalIters }
  }, [])

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Portfolio
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">
            R&D project portfolio
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">
            Active formulation projects across the team. Closed-loop optimization runs an
            inner DOE loop per project and rolls progress up here.
          </p>
        </div>
        <Button asChild>
          <Link to="/upload">
            <Sparkles className="h-4 w-4" />
            Start new project
          </Link>
        </Button>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Active projects" value={stats.total} accent="brand" hint={`${stats.iterating} iterating`} />
        <StatTile label="Converged" value={stats.converged} accent="emerald" hint="targets met" />
        <StatTile label="Data flags" value={stats.flagged} accent="amber" hint="proposed vs actual gap" />
        <StatTile label="Iterations run" value={stats.totalIters} accent="violet" hint="across portfolio" />
      </div>

      {/* Charts area */}
      <Card className="overflow-hidden border-border/70 shadow-sm">
        <CardHeader className="flex flex-row items-start justify-between gap-4 border-b bg-gradient-to-br from-brand-muted/40 via-card to-card pb-5">
          <div>
            <CardTitle className="text-base">Portfolio signal</CardTitle>
            <CardDescription>Three lenses on the same R&D pipeline.</CardDescription>
          </div>
          <Tabs defaultValue="timeline" className="w-auto">
            <TabsList>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="trajectory">Trajectory</TabsTrigger>
              <TabsTrigger value="targets">Targets met</TabsTrigger>
            </TabsList>
            <TabsContent value="timeline" className="hidden" />
            <TabsContent value="trajectory" className="hidden" />
            <TabsContent value="targets" className="hidden" />
          </Tabs>
        </CardHeader>
        <CardContent className="pt-6">
          <Tabs defaultValue="timeline">
            <TabsList className="md:hidden">
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="trajectory">Trajectory</TabsTrigger>
              <TabsTrigger value="targets">Targets met</TabsTrigger>
            </TabsList>
            <TabsContent value="timeline" className="mt-0">
              <ChartFrame
                title="Project timelines"
                blurb="Bars show planned span; fill shows iterations completed. Dashed line is today."
                icon={TrendingUp}
              >
                <GanttChart projects={portfolioProjects} />
              </ChartFrame>
            </TabsContent>
            <TabsContent value="trajectory" className="mt-0">
              <ChartFrame
                title="Objective trajectory"
                blurb="Each project's normalized objective per iteration. Steeper is better."
                icon={TrendingUp}
              >
                <ScatterChart points={portfolioScatter} />
              </ChartFrame>
            </TabsContent>
            <TabsContent value="targets" className="mt-0">
              <ChartFrame
                title="Targets met by axis"
                blurb="Where each project sits against its primary KPI, cost, sustainability, and quality goals."
                icon={FlaskConical}
              >
                <Heatmap rows={heatmapRows} cols={heatmapCols} values={heatmapValues} />
              </ChartFrame>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Project list */}
      <Card className="border-border/70 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle className="text-base">All projects</CardTitle>
              <CardDescription>Click any row to enter the project's DOE loop.</CardDescription>
            </div>
            <span className="text-xs text-muted-foreground">{portfolioProjects.length} projects</span>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-6 py-3 text-left">Project</th>
                <th className="px-3 py-3 text-left">Team</th>
                <th className="px-3 py-3 text-left">Owner</th>
                <th className="px-3 py-3 text-left">Status</th>
                <th className="px-3 py-3 text-left">Iteration</th>
                <th className="px-3 py-3 text-left">Targets</th>
                <th className="px-6 py-3 text-right">Window</th>
              </tr>
            </thead>
            <tbody>
              {portfolioProjects.map((p) => (
                <tr key={p.id} className="group border-t hover:bg-muted/40">
                  <td className="px-6 py-3">
                    <Link
                      to={`/projects/${p.id}`}
                      className="flex items-center gap-2 font-medium text-foreground group-hover:text-brand"
                    >
                      {p.name}
                      <ArrowUpRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
                    </Link>
                    <div className="text-xs text-muted-foreground">{p.domain}</div>
                  </td>
                  <td className="px-3 py-3 text-muted-foreground">{p.team}</td>
                  <td className="px-3 py-3 text-muted-foreground">{p.owner}</td>
                  <td className="px-3 py-3">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-3 py-3">
                    <IterationBar value={p.iteration} max={p.maxIterations} />
                  </td>
                  <td className="px-3 py-3 text-muted-foreground tabular-nums">
                    {p.targetsMet} / {p.targetsTotal}
                  </td>
                  <td className="px-6 py-3 text-right text-xs text-muted-foreground tabular-nums">
                    {fmt(p.startedAt)} → {fmt(p.endsAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
}

function StatTile({
  label,
  value,
  hint,
  accent,
}: {
  label: string
  value: number
  hint: string
  accent: 'brand' | 'emerald' | 'amber' | 'violet'
}) {
  const accents = {
    brand: 'from-brand/10 to-brand/0 text-brand',
    emerald: 'from-emerald-500/10 to-emerald-500/0 text-emerald-600',
    amber: 'from-amber-500/10 to-amber-500/0 text-amber-600',
    violet: 'from-violet-500/10 to-violet-500/0 text-violet-600',
  } as const
  return (
    <div className={`relative overflow-hidden rounded-xl border bg-card p-4 shadow-sm`}>
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${accents[accent]}`} />
      <div className="relative">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
        <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground">{value}</p>
        <p className="mt-0.5 text-[11px] text-muted-foreground">{hint}</p>
      </div>
    </div>
  )
}

function ChartFrame({
  title,
  blurb,
  icon: Icon,
  children,
}: {
  title: string
  blurb: string
  icon: typeof FlaskConical
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="mb-3 flex items-start gap-2">
        <Icon className="mt-0.5 h-4 w-4 text-brand" />
        <div>
          <p className="text-sm font-medium text-foreground">{title}</p>
          <p className="text-xs text-muted-foreground">{blurb}</p>
        </div>
      </div>
      <div className="rounded-lg border bg-card/40 p-4">{children}</div>
    </div>
  )
}

function IterationBar({ value, max }: { value: number; max: number }) {
  const segments = Array.from({ length: max }, (_, i) => i < value)
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {segments.map((done, i) => (
          <span
            key={i}
            className={
              done
                ? 'h-2 w-4 rounded-sm bg-brand'
                : 'h-2 w-4 rounded-sm bg-muted'
            }
          />
        ))}
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">
        {value}/{max}
      </span>
    </div>
  )
}
