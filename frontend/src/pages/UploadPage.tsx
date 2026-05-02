import { useEffect, useState } from 'react'
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
import { apiFetch, ApiError, getToken } from '@/lib/api'
import { cn } from '@/lib/utils'

interface ParsedIngredient { name: string; unit: string | null }
interface ParsedProperty { name: string; unit: string | null }
interface ParsedProduct { label: string; ingredients: Record<string, number>; properties: Record<string, number> }
interface ParsedTarget { property_name: string; goal: string; reference_label: string | null }
interface ParsedUploadResponse {
  ingredients: ParsedIngredient[]
  properties: ParsedProperty[]
  base_products: ParsedProduct[]
  targets: ParsedTarget[]
}

type Stage = 'idle' | 'parsing' | 'ready' | 'creating'

export function UploadPage() {
  const navigate = useNavigate()
  const [stage, setStage] = useState<Stage>('idle')
  const [file, setFile] = useState<File | null>(null)
  const [parsed, setParsed] = useState<ParsedUploadResponse | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  // Project metadata
  const [projName, setProjName] = useState('')
  const [projTeamId, setProjTeamId] = useState('')
  const [teams, setTeams] = useState<{ id: string; name: string }[]>([])
  const [projDomain, setProjDomain] = useState('')
  const [projStartedAt, setProjStartedAt] = useState('')
  const [projEndsAt, setProjEndsAt] = useState('')
  const [projMaxIter, setProjMaxIter] = useState('6')

  useEffect(() => {
    apiFetch<{ id: string; name: string }[]>('/teams')
      .then(setTeams)
      .catch(() => {})
  }, [])

  async function parseFile(f: File) {
    setFile(f)
    setParseError(null)
    setStage('parsing')
    try {
      const fd = new FormData()
      fd.append('file', f)
      const result = await apiFetch<ParsedUploadResponse>('/projects/parse-upload', {
        method: 'POST',
        body: fd,
      })
      setParsed(result)
      setStage('ready')
    } catch (e) {
      setParseError(e instanceof ApiError ? e.detail : 'Parse failed')
      setStage('idle')
    }
  }

  async function handleUseSample() {
    setParseError(null)
    setStage('parsing')
    try {
      const token = getToken()
      const resp = await fetch('/api/projects/sample-xlsx', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!resp.ok) throw new Error('Could not load sample')
      const blob = await resp.blob()
      const sampleFile = new File([blob], 'paint-example.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      await parseFile(sampleFile)
    } catch (e) {
      setParseError(e instanceof Error ? e.message : 'Failed to load sample')
      setStage('idle')
    }
  }

  async function handleCreate() {
    if (!file || !projName.trim()) return
    setStage('creating')
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('name', projName.trim())
      fd.append('team_id', projTeamId)
      fd.append('domain', projDomain.trim())
      fd.append('started_at', projStartedAt.trim())
      fd.append('ends_at', projEndsAt.trim())
      fd.append('max_iterations', projMaxIter || '6')
      const created = await apiFetch<{ id: string }>('/projects/upload', {
        method: 'POST',
        body: fd,
      })
      navigate(`/projects/${created.id}`)
    } catch (e) {
      setParseError(e instanceof ApiError ? e.detail : 'Create failed')
      setStage('ready')
    }
  }

  const previewIngs = parsed?.ingredients.slice(0, 4) ?? []
  const previewProps = parsed?.properties.slice(0, 2) ?? []
  const hasMore = (parsed?.ingredients.length ?? 0) > 4

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
          expressions, then create the project ready for the first iteration.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="flex flex-col gap-6">
          {/* Metadata */}
          <Card className="border-border/70 shadow-sm">
            <CardHeader className="border-b">
              <CardTitle className="text-base">1 · Project details</CardTitle>
              <CardDescription>Name this project before or after uploading.</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-4 pt-5 sm:grid-cols-3 sm:grid-rows-2">
              <div className="sm:col-span-3">
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                  Project name <span className="text-destructive">*</span>
                </label>
                <input
                  value={projName}
                  onChange={(e) => setProjName(e.target.value)}
                  placeholder="e.g. Low-VOC Architectural Paint"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Team</label>
                <select
                  value={projTeamId}
                  onChange={(e) => setProjTeamId(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">— None —</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Domain</label>
                <input
                  value={projDomain}
                  onChange={(e) => setProjDomain(e.target.value)}
                  placeholder="e.g. Coatings"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Start date</label>
                <input
                  type="date"
                  value={projStartedAt}
                  onChange={(e) => setProjStartedAt(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">End date (planned)</label>
                <input
                  type="date"
                  value={projEndsAt}
                  onChange={(e) => setProjEndsAt(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Max iterations</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={projMaxIter}
                  onChange={(e) => setProjMaxIter(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </CardContent>
          </Card>

          {/* Dropzone */}
          <Card className="border-border/70 shadow-sm">
            <CardHeader className="border-b">
              <CardTitle className="text-base">2 · Drop your file</CardTitle>
              <CardDescription>
                XLSX matching the Phase 1 template — Products + Targets sheets.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              {(stage === 'idle' || stage === 'ready') && (
                <>
                  {stage === 'idle' && (
                    <label
                      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                      onDragLeave={() => setDragOver(false)}
                      onDrop={(e) => {
                        e.preventDefault()
                        setDragOver(false)
                        const f = e.dataTransfer.files?.[0]
                        if (f) parseFile(f)
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
                          Up to 10 MB. Templates in <code>docs/upload-template/</code>.
                        </p>
                      </div>
                      <input
                        type="file"
                        accept=".xlsx,.xls"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0]
                          if (f) parseFile(f)
                        }}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.preventDefault(); handleUseSample() }}
                      >
                        <FileSpreadsheet className="h-3.5 w-3.5" />
                        Use the paint sample
                      </Button>
                    </label>
                  )}

                  {parseError && (
                    <p className="mt-3 text-sm text-destructive">{parseError}</p>
                  )}

                  {stage === 'ready' && parsed && (
                    <div className="space-y-6">
                      <div className="flex items-center gap-3 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-700">
                        <CheckCircle2 className="h-4 w-4 shrink-0" />
                        <p className="text-sm font-medium">
                          Parsed <code className="font-mono">{file?.name}</code> ·{' '}
                          {parsed.base_products.length} base products · {parsed.ingredients.length} ingredients ·{' '}
                          {parsed.properties.length} properties · {parsed.targets.length} targets
                        </p>
                      </div>

                      {/* Products preview */}
                      <div>
                        <div className="mb-2 flex items-center justify-between">
                          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            <FlaskConical className="h-3 w-3" />
                            Products sheet · preview
                          </p>
                          <Badge variant="muted">{parsed.base_products.length} rows</Badge>
                        </div>
                        <div className="overflow-x-auto rounded-lg border">
                          <table className="w-full text-xs">
                            <thead className="bg-muted/40 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                              <tr>
                                <th className="px-3 py-2 text-left">Product</th>
                                {previewIngs.map((ing) => (
                                  <th key={ing.name} className="px-3 py-2 text-right">
                                    <span className="text-brand">Ingredient:</span><br />
                                    {ing.name}
                                    <div className="font-normal normal-case text-muted-foreground/70">
                                      {ing.unit ? `(${ing.unit})` : ''}
                                    </div>
                                  </th>
                                ))}
                                {hasMore && <th className="px-3 py-2 text-right text-muted-foreground">…</th>}
                                {previewProps.map((prop) => (
                                  <th key={prop.name} className="bg-violet-50/50 px-3 py-2 text-right">
                                    <span className="text-violet-700">Property:</span><br />
                                    {prop.name}
                                    <div className="font-normal normal-case text-muted-foreground/70">
                                      {prop.unit ? `(${prop.unit})` : ''}
                                    </div>
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {parsed.base_products.map((bp) => (
                                <tr key={bp.label} className="border-t">
                                  <td className="px-3 py-2 font-medium text-foreground">{bp.label}</td>
                                  {previewIngs.map((ing) => (
                                    <td key={ing.name} className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                                      {bp.ingredients[ing.name] ?? '—'}
                                    </td>
                                  ))}
                                  {hasMore && <td className="px-3 py-2 text-right text-muted-foreground">…</td>}
                                  {previewProps.map((prop) => (
                                    <td key={prop.name} className="bg-violet-50/30 px-3 py-2 text-right tabular-nums text-foreground">
                                      {bp.properties[prop.name] ?? '—'}
                                    </td>
                                  ))}
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
                          <Badge variant="muted">{parsed.targets.length} goals</Badge>
                        </div>
                        <div className="overflow-hidden rounded-lg border">
                          <table className="w-full text-xs">
                            <thead className="bg-muted/40 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                              <tr>
                                <th className="px-3 py-2 text-left">Property</th>
                                <th className="px-3 py-2 text-left">Goal</th>
                                <th className="px-3 py-2 text-left">Reference</th>
                                <th className="px-3 py-2 text-left">Meaning</th>
                              </tr>
                            </thead>
                            <tbody>
                              {parsed.targets.map((t) => (
                                <tr key={t.property_name} className="border-t">
                                  <td className="px-3 py-2 font-medium text-foreground">{t.property_name}</td>
                                  <td className="px-3 py-2">
                                    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">{t.goal}</code>
                                  </td>
                                  <td className="px-3 py-2 text-muted-foreground">{t.reference_label ?? '—'}</td>
                                  <td className="px-3 py-2 text-muted-foreground">{describeGoal(t.goal, t.reference_label)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      <div className="flex items-center justify-between gap-3 border-t pt-4">
                        <Button variant="outline" onClick={() => { setStage('idle'); setParsed(null); setFile(null) }}>
                          Replace file
                        </Button>
                        <Button
                          onClick={handleCreate}
                          disabled={!projName.trim()}
                          title={!projName.trim() ? 'Enter a project name above' : undefined}
                        >
                          <Sparkles className="h-4 w-4" />
                          Create project
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}

              {(stage === 'parsing' || stage === 'creating') && (
                <div className="flex flex-col items-center gap-3 py-12 text-center">
                  <div className="relative">
                    <div className="h-12 w-12 rounded-full border-2 border-brand/20" />
                    <div className="absolute inset-0 h-12 w-12 animate-spin rounded-full border-2 border-transparent border-t-brand" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {stage === 'parsing' ? `Parsing ${file?.name ?? 'file'}…` : 'Creating project…'}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {stage === 'parsing'
                        ? 'Reading Products sheet → detecting ingredients/properties → parsing goal DSL'
                        : 'Saving ingredients, targets, and base products to database'}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

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
                <p className="text-xs font-semibold uppercase tracking-wider">Sample files</p>
              </div>
              <p className="text-sm font-medium text-foreground">Three templates ready to use.</p>
              <ul className="space-y-1 text-xs text-muted-foreground">
                <li><code>paint-example.xlsx</code> — architectural paint</li>
                <li><code>epoxy-adhesive-sample.xlsx</code> — high-temp epoxy</li>
                <li><code>detergent-sample.xlsx</code> — cold-wash detergent</li>
              </ul>
              <p className="text-xs text-muted-foreground">
                All in <code>docs/upload-samples/</code>.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function describeGoal(goal: string, ref?: string | null): string {
  const t = goal.replace(/\s/g, '')
  if (t.startsWith('>=')) return `at least ${t.slice(2)}`
  if (t.startsWith('<=')) return `at most ${t.slice(2)}`
  if (t.startsWith('=')) return `equal to ${t.slice(1)} (±0.1%)`
  if (/^[+-]\d+(\.\d+)?%$/.test(t)) return `${t} vs ${ref ?? 'reference'}`
  if (t.startsWith('[')) return `within range ${t}`
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
