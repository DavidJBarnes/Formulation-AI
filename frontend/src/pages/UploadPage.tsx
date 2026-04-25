import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  CheckCircle2,
  FileSpreadsheet,
  FlaskConical,
  Sparkles,
  Target,
  UploadCloud,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { paintIngredients, paintProject, paintProperties } from '@/data/fixtures'
import { cn } from '@/lib/utils'

type Stage = 'idle' | 'parsing' | 'parsed'

export function UploadPage() {
  const navigate = useNavigate()
  const [stage, setStage] = useState<Stage>('idle')
  const [filename, setFilename] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFile = (file: File) => {
    setFilename(file.name)
    setStage('parsing')
    // Simulate parse — in real product this hits backend XLSX parser
    setTimeout(() => setStage('parsed'), 900)
  }

  const handleUseSample = () => {
    setFilename('paint-example.xlsx')
    setStage('parsing')
    setTimeout(() => setStage('parsed'), 700)
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          New project
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">
          Upload base products and targets
        </h1>
        <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">
          Drop the Phase 1 XLSX template. We'll detect ingredients, properties, and goal
          expressions, then propose the first iteration of candidates.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        {/* Dropzone column */}
        <Card className="border-border/70 shadow-sm">
          <CardHeader className="border-b">
            <CardTitle className="text-base">1 · Drop your file</CardTitle>
            <CardDescription>
              XLSX matching the Phase 1 template — Products + Targets sheets.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            {stage === 'idle' && (
              <label
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragOver(false)
                  const f = e.dataTransfer.files?.[0]
                  if (f) handleFile(f)
                }}
                className={cn(
                  'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border bg-gradient-to-b from-muted/30 to-card px-6 py-12 text-center transition-colors',
                  dragOver && 'border-brand bg-brand-muted/40',
                )}
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-muted text-brand">
                  <UploadCloud className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">
                    Drop XLSX here, or <span className="text-brand">browse</span>
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Up to 10 MB. The template lives in <code>docs/upload-template/</code>.
                  </p>
                </div>
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) handleFile(f)
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.preventDefault()
                    handleUseSample()
                  }}
                >
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                  Use the paint sample
                </Button>
              </label>
            )}

            {stage === 'parsing' && (
              <div className="flex flex-col items-center gap-3 py-12 text-center">
                <div className="relative">
                  <div className="h-12 w-12 rounded-full border-2 border-brand/20" />
                  <div className="absolute inset-0 h-12 w-12 animate-spin rounded-full border-2 border-transparent border-t-brand" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">Parsing {filename}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Reading Products sheet → detecting ingredient/property columns → parsing goal DSL
                  </p>
                </div>
              </div>
            )}

            {stage === 'parsed' && (
              <div className="space-y-6">
                <div className="flex items-center gap-3 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" />
                  <p className="text-sm font-medium">
                    Parsed <code className="font-mono">{filename}</code> · 2 base products, {paintIngredients.length} ingredients,{' '}
                    {paintProperties.length} properties, {paintProject.targets.length} targets
                  </p>
                </div>

                {/* Products preview */}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <FlaskConical className="h-3 w-3" />
                      Products sheet · preview
                    </p>
                    <Badge variant="muted">2 rows</Badge>
                  </div>
                  <div className="overflow-x-auto rounded-lg border">
                    <table className="w-full text-xs">
                      <thead className="bg-muted/40 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        <tr>
                          <th className="px-3 py-2 text-left">Product</th>
                          {paintIngredients.slice(0, 4).map((ing) => (
                            <th key={ing.name} className="px-3 py-2 text-right">
                              <span className="text-brand">Ingredient:</span>
                              <br />
                              {ing.name}
                              <div className="font-normal normal-case text-muted-foreground/70">({ing.unit})</div>
                            </th>
                          ))}
                          <th className="px-3 py-2 text-right text-muted-foreground">…</th>
                          {paintProperties.slice(0, 2).map((prop) => (
                            <th key={prop.name} className="bg-violet-50/50 px-3 py-2 text-right">
                              <span className="text-violet-700">Property:</span>
                              <br />
                              {prop.name}
                              <div className="font-normal normal-case text-muted-foreground/70">
                                {prop.unit ? `(${prop.unit})` : ''}
                              </div>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {paintProject.baseProducts.map((b) => (
                          <tr key={b.id} className="border-t">
                            <td className="px-3 py-2 font-medium text-foreground">{b.label}</td>
                            {paintIngredients.slice(0, 4).map((ing) => (
                              <td key={ing.name} className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                                {b.ingredients[ing.name]}
                              </td>
                            ))}
                            <td className="px-3 py-2 text-right text-muted-foreground">…</td>
                            {paintProperties.slice(0, 2).map((prop) => {
                              const m = b.properties.find((p) => p.name === prop.name)
                              return (
                                <td key={prop.name} className="bg-violet-50/30 px-3 py-2 text-right tabular-nums text-foreground">
                                  {m ? m.value : '—'}
                                </td>
                              )
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Targets preview */}
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <Target className="h-3 w-3" />
                      Targets sheet · preview
                    </p>
                    <Badge variant="muted">{paintProject.targets.length} goals</Badge>
                  </div>
                  <div className="overflow-hidden rounded-lg border">
                    <table className="w-full text-xs">
                      <thead className="bg-muted/40 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        <tr>
                          <th className="px-3 py-2 text-left">Property</th>
                          <th className="px-3 py-2 text-left">Goal</th>
                          <th className="px-3 py-2 text-left">Reference</th>
                          <th className="px-3 py-2 text-left">Parsed</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paintProject.targets.map((t) => (
                          <tr key={t.property} className="border-t">
                            <td className="px-3 py-2 font-medium text-foreground">{t.property}</td>
                            <td className="px-3 py-2">
                              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">{t.goal}</code>
                            </td>
                            <td className="px-3 py-2 text-muted-foreground">{t.reference ?? '—'}</td>
                            <td className="px-3 py-2 text-muted-foreground">{describeGoal(t.goal, t.reference)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 border-t pt-4">
                  <Button variant="outline" onClick={() => setStage('idle')}>
                    Replace file
                  </Button>
                  <Button onClick={() => navigate('/projects/paint-low-voc')}>
                    <Sparkles className="h-4 w-4" />
                    Create project & propose I1
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Side panel */}
        <div className="space-y-4">
          <Card className="border-border/70 shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm">What we expect</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-muted-foreground">
              <Step
                n={1}
                title="Products sheet (wide)"
                body={
                  <>
                    One row per formulation. Columns prefixed{' '}
                    <code className="rounded bg-muted px-1">Ingredient:</code> /{' '}
                    <code className="rounded bg-muted px-1">Property:</code>, unit in parens.
                  </>
                }
              />
              <Step
                n={2}
                title="Targets sheet"
                body={
                  <>
                    One row per goal. Mini-DSL on the Goal column:{' '}
                    <code className="rounded bg-muted px-1">=N</code>,{' '}
                    <code className="rounded bg-muted px-1">&gt;=N</code>,{' '}
                    <code className="rounded bg-muted px-1">&lt;=N</code>,{' '}
                    <code className="rounded bg-muted px-1">+N%</code>,{' '}
                    <code className="rounded bg-muted px-1">[a,b]</code>.
                  </>
                }
              />
              <Step
                n={3}
                title="Propose"
                body="Claude Opus 4.7 reads your base + targets and proposes K candidates with predicted (value ± σ) and a rationale per candidate."
              />
            </CardContent>
          </Card>

          <Card className="border-brand/30 bg-brand-muted/30 shadow-sm">
            <CardContent className="space-y-2 pt-6">
              <div className="flex items-center gap-2 text-brand">
                <Sparkles className="h-4 w-4" />
                <p className="text-xs font-semibold uppercase tracking-wider">Phase 1</p>
              </div>
              <p className="text-sm font-medium text-foreground">
                LLM-only proposals on day one.
              </p>
              <p className="text-xs text-muted-foreground">
                A real Bayesian optimizer (GP/BO) slots in for Phase 2 behind the same
                API — your data carries over.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function describeGoal(goal: string, ref?: string): string {
  const t = goal.replace(/\s/g, '')
  if (t.startsWith('>=')) return `at least ${t.slice(2)}`
  if (t.startsWith('<=')) return `at most ${t.slice(2)}`
  if (t.startsWith('=')) return `equal to ${t.slice(1)} (±3%)`
  if (/^[+-]\d+(\.\d+)?%$/.test(t)) return `${t} vs ${ref ?? 'reference'}`
  if (t.startsWith('[')) return `within range`
  return goal
}

function Step({ n, title, body }: { n: number; title: string; body: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand text-[10px] font-semibold text-white">
        {n}
      </span>
      <div>
        <p className="text-xs font-medium text-foreground">{title}</p>
        <p className="mt-0.5 text-[11px] leading-snug">{body}</p>
      </div>
    </div>
  )
}
