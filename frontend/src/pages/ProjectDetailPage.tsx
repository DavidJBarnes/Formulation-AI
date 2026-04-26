import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Beaker,
  Brain,
  CheckCircle2,
  Clock,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { StatusBadge } from '@/components/StatusBadge'
import { apiFetch } from '@/lib/api'
import type { Formulation, Iteration, ProjectDetail, Target as TTarget } from '@/data/types'
import { cn } from '@/lib/utils'

// ---------------------------------------------------------------------------
// API response shape (snake_case)
// ---------------------------------------------------------------------------
interface ApiFormulation {
  id: string
  label: string
  kind: 'base' | 'tested' | 'proposed'
  iteration_n: number | null
  rationale?: string | null
  flagged: boolean
  ingredients: Record<string, number>
  properties: { name: string; unit: string | null; value: number; sigma?: number | null }[]
}

interface ApiIterationSummary {
  n: number
  best_objective: number | null
  status: string
  note?: string | null
}

interface ApiProjectDetail {
  id: string
  name: string
  team: string | null
  owner_name: string | null
  status: string
  started_at: string | null
  ends_at: string | null
  domain: string | null
  current_iteration: number
  max_iterations: number
  targets_met: number
  targets_total: number
  flag_note?: string | null
  iterations: ApiIterationSummary[]
  ingredients: { name: string; unit: string | null; min_amount?: number | null; max_amount?: number | null }[]
  targets: { property_name: string; unit: string | null; goal: string; reference_label?: string | null }[]
  base_products: ApiFormulation[]
  tested: ApiFormulation[]
  proposed: ApiFormulation[]
}

// ---------------------------------------------------------------------------
// Adapter: API → frontend types
// ---------------------------------------------------------------------------
function adaptFormulation(f: ApiFormulation): Formulation {
  return {
    id: f.id,
    label: f.label,
    kind: f.kind,
    iteration: f.iteration_n ?? 0,
    rationale: f.rationale ?? undefined,
    flagged: f.flagged,
    ingredients: f.ingredients,
    properties: f.properties.map((p) => ({
      name: p.name,
      unit: p.unit ?? '',
      value: p.value,
      sigma: p.sigma ?? undefined,
    })),
  }
}

function adaptIterationStatus(status: string): Iteration['status'] {
  if (status === 'in_progress') return 'in-progress'
  if (status === 'done') return 'done'
  return 'queued'
}

function adaptProjectDetail(api: ApiProjectDetail): ProjectDetail {
  return {
    id: api.id,
    name: api.name,
    team: api.team ?? '',
    owner: api.owner_name ?? '',
    status: api.status as ProjectDetail['status'],
    domain: api.domain ?? '',
    startedAt: api.started_at ?? '',
    endsAt: api.ends_at ?? '',
    iteration: api.current_iteration,
    maxIterations: api.max_iterations,
    flagNote: api.flag_note ?? undefined,
    ingredients: api.ingredients.map((i) => ({
      name: i.name,
      unit: i.unit ?? '',
      min: i.min_amount ?? undefined,
      max: i.max_amount ?? undefined,
    })),
    targets: api.targets.map((t) => ({
      property: t.property_name,
      unit: t.unit ?? '',
      goal: t.goal,
      reference: t.reference_label ?? undefined,
    })),
    iterations: api.iterations.map((it) => ({
      n: it.n,
      date: '',
      candidates: 0,
      bestObjective: it.best_objective ?? 0,
      status: adaptIterationStatus(it.status),
      note: it.note ?? undefined,
    })),
    baseProducts: api.base_products.map(adaptFormulation),
    tested: api.tested.map(adaptFormulation),
    proposed: api.proposed.map(adaptFormulation),
  }
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------
export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    apiFetch<ApiProjectDetail>(`/projects/${id}`)
      .then((data) => setProject(adaptProjectDetail(data)))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [id])

  const targetEval = useMemo(() => {
    if (!project) return []
    const referenceProperty = (name: string) =>
      project.baseProducts
        .find((b) => b.label.includes('Paint A'))
        ?.properties.find((p) => p.name === name)
    return project.targets.map((t) => {
      const ref = referenceProperty(t.property)?.value ?? null
      const lastTested = [...project.tested]
        .reverse()
        .find((f) => f.properties.some((p) => p.name === t.property))
      const latest = lastTested?.properties.find((p) => p.name === t.property)?.value ?? null
      return { target: t, ref, latest, met: evaluateGoal(t.goal, latest, ref) }
    })
  }, [project])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-destructive">
        {error ?? 'Project not found'}
      </div>
    )
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8">
      {/* Breadcrumb + header */}
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" />
          Portfolio
        </Link>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {project.team} · {project.domain}
            </p>
            <h1 className="mt-1 flex items-center gap-3 text-2xl font-semibold tracking-tight text-foreground">
              {project.name}
              <StatusBadge status={project.status} />
            </h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Owner {project.owner} · iteration {project.iteration} of {project.maxIterations} ·
              window {fmt(project.startedAt)} → {fmt(project.endsAt)}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline">
              <Clock className="h-4 w-4" />
              Log results
            </Button>
            <Button>
              <Sparkles className="h-4 w-4" />
              Run next iteration
            </Button>
          </div>
        </div>
      </div>

      {/* Targets row */}
      <div className="grid gap-3 md:grid-cols-3">
        {targetEval.map(({ target, ref, latest, met }) => (
          <TargetTile key={target.property} target={target} ref={ref} latest={latest} met={met} />
        ))}
      </div>

      {/* Iteration timeline */}
      <Card className="border-border/70 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Iteration timeline</CardTitle>
              <CardDescription>The DOE inner loop, 3 → 6 cycles.</CardDescription>
            </div>
            <ObjectiveSpark
              series={project.iterations.map((it) => it.bestObjective)}
            />
          </div>
        </CardHeader>
        <CardContent className="py-6">
          <div className="flex flex-wrap items-stretch gap-3">
            {project.iterations.map((it, idx) => (
              <IterationCard
                key={it.n}
                iteration={it}
                isLast={idx === project.iterations.length - 1}
              />
            ))}
            <PendingIterationCard nextN={project.iterations.length + 1} max={project.maxIterations} />
          </div>
        </CardContent>
      </Card>

      {/* Proposals + tested formulations */}
      <Tabs defaultValue="proposals" className="w-full">
        <TabsList>
          <TabsTrigger value="proposals" className="gap-1.5">
            <Brain className="h-3.5 w-3.5" />
            AI proposals · I{project.iteration}
          </TabsTrigger>
          <TabsTrigger value="tested" className="gap-1.5">
            <Beaker className="h-3.5 w-3.5" />
            Tested formulations
          </TabsTrigger>
          <TabsTrigger value="base" className="gap-1.5">
            Base products
          </TabsTrigger>
        </TabsList>

        <TabsContent value="proposals">
          <div className="grid gap-4 lg:grid-cols-3">
            {project.proposed.map((f) => (
              <ProposalCard
                key={f.id}
                formulation={f}
                targets={project.targets}
                ingredients={project.ingredients}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="tested">
          <Card className="border-border/70 shadow-sm">
            <CardContent className="overflow-x-auto p-0">
              <FormulationTable
                formulations={project.tested}
                targets={project.targets}
                ingredients={project.ingredients}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="base">
          <Card className="border-border/70 shadow-sm">
            <CardContent className="overflow-x-auto p-0">
              <FormulationTable
                formulations={project.baseProducts}
                targets={project.targets}
                ingredients={project.ingredients}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function evaluateGoal(goal: string, value: number | null, ref: number | null): 'met' | 'partial' | 'miss' | 'unknown' {
  if (value == null) return 'unknown'
  const trimmed = goal.replace(/\s/g, '')
  let lo: number | null = null
  let hi: number | null = null
  if (trimmed.startsWith('=')) {
    const n = Number(trimmed.slice(1))
    lo = n * 0.97
    hi = n * 1.03
  } else if (trimmed.startsWith('>=')) {
    lo = Number(trimmed.slice(2))
  } else if (trimmed.startsWith('<=')) {
    hi = Number(trimmed.slice(2))
  } else if (/^[+-]\d+(\.\d+)?%$/.test(trimmed)) {
    if (ref == null) return 'unknown'
    const pct = Number(trimmed.replace('%', '')) / 100
    const target = ref * (1 + pct)
    if (pct >= 0) lo = target
    else hi = target
  } else {
    const m = trimmed.match(/^\[(-?\d+(\.\d+)?),(-?\d+(\.\d+)?)\]$/)
    if (m) {
      lo = Number(m[1])
      hi = Number(m[3])
    }
  }
  const okLo = lo == null || value >= lo
  const okHi = hi == null || value <= hi
  if (okLo && okHi) return 'met'
  // partial if within 5% of bound
  const slack = lo != null ? Math.abs((value - lo) / lo) : hi != null ? Math.abs((value - hi) / hi) : 1
  return slack < 0.05 ? 'partial' : 'miss'
}

function TargetTile({
  target,
  ref,
  latest,
  met,
}: {
  target: TTarget
  ref: number | null
  latest: number | null
  met: 'met' | 'partial' | 'miss' | 'unknown'
}) {
  const tone = {
    met: 'border-emerald-200 bg-emerald-50/60',
    partial: 'border-amber-200 bg-amber-50/60',
    miss: 'border-rose-200 bg-rose-50/60',
    unknown: 'border-border bg-card',
  }[met]
  const dot = {
    met: 'bg-emerald-500',
    partial: 'bg-amber-500',
    miss: 'bg-rose-500',
    unknown: 'bg-muted-foreground/40',
  }[met]
  return (
    <div className={cn('relative overflow-hidden rounded-xl border p-4', tone)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Target className="h-3 w-3" />
            Target
          </p>
          <p className="mt-1 text-sm font-semibold text-foreground">{target.property}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Goal <code className="font-mono">{target.goal}</code>
            {target.reference ? ` vs ${target.reference}` : ''}
            {target.unit ? ` · ${target.unit}` : ''}
          </p>
        </div>
        <span className={cn('mt-1 h-2 w-2 rounded-full', dot)} />
      </div>
      <div className="mt-3 flex items-end gap-3">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Latest</p>
          <p className="text-xl font-semibold tabular-nums text-foreground">
            {latest != null ? formatNumber(latest) : '—'}
            {target.unit && <span className="ml-1 text-xs font-normal text-muted-foreground">{target.unit}</span>}
          </p>
        </div>
        {ref != null && (
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Ref</p>
            <p className="text-sm tabular-nums text-muted-foreground">{formatNumber(ref)}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function IterationCard({ iteration, isLast }: { iteration: Iteration; isLast: boolean }) {
  const Icon = iteration.status === 'done' ? CheckCircle2 : iteration.status === 'in-progress' ? Clock : Beaker
  const tone =
    iteration.status === 'done'
      ? 'border-emerald-200 bg-emerald-50/60 text-emerald-700'
      : iteration.status === 'in-progress'
      ? 'border-brand/30 bg-brand-muted/60 text-brand'
      : 'border-border bg-card text-muted-foreground'
  return (
    <div className={cn('relative w-44 shrink-0 rounded-xl border p-3', tone)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider">I{iteration.n}</span>
        <Icon className="h-3.5 w-3.5" />
      </div>
      {iteration.date && (
        <p className="mt-1 text-[11px] opacity-80">{iteration.date}</p>
      )}
      <p className="mt-3 text-[10px] uppercase tracking-wider opacity-70">Best objective</p>
      <p className="text-xl font-semibold tabular-nums text-foreground">
        {Math.round(iteration.bestObjective * 100)}%
      </p>
      {iteration.candidates > 0 && (
        <p className="mt-1.5 text-[11px] text-muted-foreground">
          {iteration.candidates} candidate{iteration.candidates === 1 ? '' : 's'}
        </p>
      )}
      {iteration.note && (
        <p className="mt-2 text-[11px] italic text-muted-foreground">{iteration.note}</p>
      )}
      {!isLast && (
        <span className="absolute -right-2 top-1/2 hidden h-px w-3 -translate-y-1/2 bg-border md:block" />
      )}
    </div>
  )
}

function PendingIterationCard({ nextN, max }: { nextN: number; max: number }) {
  if (nextN > max) return null
  return (
    <div className="flex w-44 shrink-0 flex-col items-start justify-between rounded-xl border border-dashed border-border bg-card/50 p-3 text-muted-foreground">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider">I{nextN}</span>
      </div>
      <p className="mt-3 text-[11px]">Next, after I{nextN - 1} results land.</p>
      <Button variant="outline" size="sm" className="mt-3 w-full" disabled>
        <Sparkles className="h-3 w-3" />
        Propose
      </Button>
    </div>
  )
}

function ObjectiveSpark({ series }: { series: number[] }) {
  if (series.length < 2) return null
  const w = 120
  const h = 32
  const max = Math.max(...series)
  const min = Math.min(...series)
  const span = max - min || 1
  const path = series
    .map((v, i) => {
      const x = (i / (series.length - 1)) * (w - 4) + 2
      const y = h - 4 - ((v - min) / span) * (h - 8)
      return `${i === 0 ? 'M' : 'L'}${x},${y}`
    })
    .join(' ')
  return (
    <div className="hidden items-center gap-2 md:flex">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Trend</span>
      <svg width={w} height={h} className="overflow-visible">
        <path d={path} fill="none" stroke="hsl(221 83% 50%)" strokeWidth={1.5} />
        {series.map((v, i) => {
          const x = (i / (series.length - 1)) * (w - 4) + 2
          const y = h - 4 - ((v - min) / span) * (h - 8)
          return <circle key={i} cx={x} cy={y} r={2.5} fill="hsl(221 83% 50%)" />
        })}
      </svg>
      <TrendingUp className="h-3.5 w-3.5 text-brand" />
    </div>
  )
}

function ProposalCard({
  formulation,
  targets,
  ingredients,
}: {
  formulation: Formulation
  targets: TTarget[]
  ingredients: { name: string; unit: string }[]
}) {
  const total = ingredients.reduce((s, ing) => s + (formulation.ingredients[ing.name] ?? 0), 0)
  return (
    <Card className="overflow-hidden border-border/70 shadow-sm">
      <div className="bg-gradient-to-br from-brand-muted/40 via-card to-card p-4">
        <div className="flex items-center justify-between">
          <div>
            <Badge variant="info" className="font-mono">
              {formulation.label}
            </Badge>
            <p className="mt-2 text-sm font-semibold text-foreground">Iteration {formulation.iteration} candidate</p>
          </div>
          <div className="flex items-center gap-1 text-brand">
            <Brain className="h-4 w-4" />
            <span className="text-[10px] font-semibold uppercase tracking-wider">Claude Opus 4.7</span>
          </div>
        </div>
      </div>
      <CardContent className="space-y-4 pt-4">
        {/* Predicted properties */}
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Predicted properties · value ± 1σ
          </p>
          <div className="space-y-2">
            {formulation.properties.map((p) => {
              const target = targets.find((t) => t.property === p.name)
              return (
                <div key={p.name} className="flex items-center justify-between gap-3 rounded-md bg-muted/40 px-3 py-2">
                  <div>
                    <p className="text-xs font-medium text-foreground">{p.name}</p>
                    <p className="text-[10px] text-muted-foreground">
                      Goal {target?.goal ?? '—'} {p.unit && `· ${p.unit}`}
                    </p>
                  </div>
                  <div className="text-right tabular-nums">
                    <p className="text-sm font-semibold text-foreground">
                      {formatNumber(p.value)}
                      {p.sigma != null && (
                        <span className="ml-1 text-xs font-normal text-muted-foreground">
                          ± {formatNumber(p.sigma)}
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Ingredient mix */}
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Ingredient mix
          </p>
          <div className="space-y-1.5">
            {ingredients.map((ing) => {
              const v = formulation.ingredients[ing.name] ?? 0
              const pct = total > 0 ? (v / total) * 100 : 0
              return (
                <div key={ing.name} className="flex items-center gap-2 text-[11px]">
                  <span className="w-32 shrink-0 text-muted-foreground">{ing.name}</span>
                  <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <span
                      className="absolute inset-y-0 left-0 rounded-full bg-brand/70"
                      style={{ width: `${Math.min(100, pct * 1.4)}%` }}
                    />
                  </div>
                  <span className="w-16 shrink-0 text-right tabular-nums text-foreground">
                    {formatNumber(v)} {ing.unit}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Rationale */}
        {formulation.rationale && (
          <div className="rounded-md border-l-2 border-brand bg-brand-muted/40 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-brand">Rationale</p>
            <p className="mt-1 text-xs leading-relaxed text-foreground">{formulation.rationale}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function FormulationTable({
  formulations,
  targets,
  ingredients,
}: {
  formulations: Formulation[]
  targets: TTarget[]
  ingredients: { name: string; unit: string }[]
}) {
  return (
    <table className="w-full text-xs">
      <thead className="bg-muted/40 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        <tr>
          <th className="sticky left-0 bg-muted/40 px-4 py-3 text-left">Formulation</th>
          {ingredients.map((ing) => (
            <th key={ing.name} className="px-3 py-3 text-right">
              {ing.name}
              <div className="text-[9px] font-normal normal-case text-muted-foreground/70">{ing.unit}</div>
            </th>
          ))}
          {targets.map((t) => (
            <th key={t.property} className="bg-brand-muted/30 px-3 py-3 text-right">
              {t.property}
              <div className="text-[9px] font-normal normal-case text-muted-foreground/70">{t.unit}</div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {formulations.map((f) => (
          <tr key={f.id} className="border-t hover:bg-muted/30">
            <td className="sticky left-0 bg-card px-4 py-2 font-medium text-foreground">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-muted-foreground">{f.label}</span>
                {f.kind === 'base' && <Badge variant="muted">base</Badge>}
                {f.kind === 'tested' && <Badge variant="info">I{f.iteration}</Badge>}
              </div>
            </td>
            {ingredients.map((ing) => (
              <td key={ing.name} className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                {formatNumber(f.ingredients[ing.name] ?? 0)}
              </td>
            ))}
            {targets.map((t) => {
              const prop = f.properties.find((p) => p.name === t.property)
              return (
                <td key={t.property} className="bg-brand-muted/15 px-3 py-2 text-right tabular-nums font-medium text-foreground">
                  {prop ? formatNumber(prop.value) : '—'}
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function formatNumber(n: number) {
  if (Math.abs(n) >= 100) return n.toFixed(0)
  if (Math.abs(n) >= 1) return n.toFixed(2)
  return n.toFixed(3)
}
