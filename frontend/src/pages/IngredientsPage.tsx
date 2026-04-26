import { useEffect, useRef, useState } from 'react'
import { FlaskConical, Pencil, Plus, Trash2, X, Check } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { apiFetch } from '@/lib/api'
import { cn } from '@/lib/utils'

interface Ingredient {
  id: string
  name: string
  default_unit: string | null
  description: string | null
  created_at: string
  project_count: number
}

export function IngredientsPage() {
  const [ingredients, setIngredients] = useState<Ingredient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    apiFetch<Ingredient[]>('/ingredients')
      .then(setIngredients)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  async function handleDelete(id: string) {
    try {
      await apiFetch(`/ingredients/${id}`, { method: 'DELETE' })
      setIngredients((prev) => prev.filter((i) => i.id !== id))
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  async function handleSave(id: string, patch: { name: string; default_unit: string; description: string }) {
    try {
      const updated = await apiFetch<Ingredient>(`/ingredients/${id}`, {
        method: 'PATCH',
        body: {
          name: patch.name || undefined,
          default_unit: patch.default_unit || null,
          description: patch.description || null,
        },
      })
      setIngredients((prev) => prev.map((i) => (i.id === id ? updated : i)))
      setEditingId(null)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Update failed')
    }
  }

  async function handleCreate(fields: { name: string; default_unit: string; description: string }) {
    try {
      const created = await apiFetch<Ingredient>('/ingredients', {
        method: 'POST',
        body: {
          name: fields.name,
          default_unit: fields.default_unit || null,
          description: fields.description || null,
        },
      })
      setIngredients((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)))
      setAdding(false)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Create failed')
    }
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Global registry
          </p>
          <h1 className="mt-1 flex items-center gap-3 text-2xl font-semibold tracking-tight text-foreground">
            <FlaskConical className="h-6 w-6 text-brand" />
            Ingredients
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">
            Shared across all projects. Each project selects from this list and adds
            its own bounds for the optimizer.
          </p>
        </div>
        <Button onClick={() => { setAdding(true); setEditingId(null) }}>
          <Plus className="h-4 w-4" />
          Add ingredient
        </Button>
      </div>

      <Card className="border-border/70 shadow-sm">
        <CardHeader className="border-b">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">All ingredients</CardTitle>
              <CardDescription>
                {loading ? 'Loading…' : `${ingredients.length} ingredient${ingredients.length === 1 ? '' : 's'}`}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {error && (
            <div className="px-6 py-4 text-sm text-destructive">{error}</div>
          )}
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-6 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Default unit</th>
                <th className="px-4 py-3 text-left">Description</th>
                <th className="px-4 py-3 text-left">Used in</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {adding && (
                <InlineForm
                  onSave={handleCreate}
                  onCancel={() => setAdding(false)}
                />
              )}
              {ingredients.map((ing) =>
                editingId === ing.id ? (
                  <InlineForm
                    key={ing.id}
                    initial={ing}
                    onSave={(fields) => handleSave(ing.id, fields)}
                    onCancel={() => setEditingId(null)}
                  />
                ) : (
                  <tr key={ing.id} className="group border-t hover:bg-muted/30">
                    <td className="px-6 py-3 font-medium text-foreground">{ing.name}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {ing.default_unit ?? <span className="text-muted-foreground/40">—</span>}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {ing.description ?? <span className="text-muted-foreground/40">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      {ing.project_count > 0 ? (
                        <Badge variant="info">{ing.project_count} project{ing.project_count === 1 ? '' : 's'}</Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground/40">unused</span>
                      )}
                    </td>
                    <td className="px-6 py-3 text-right">
                      <div className="flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => { setEditingId(ing.id); setAdding(false) }}
                        >
                          <Pencil className="h-3 w-3" />
                          Edit
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={ing.project_count > 0}
                          onClick={() => handleDelete(ing.id)}
                          className={cn(ing.project_count === 0 && 'hover:border-destructive hover:text-destructive')}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                )
              )}
              {!loading && !adding && ingredients.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-sm text-muted-foreground">
                    No ingredients yet.{' '}
                    <button onClick={() => setAdding(true)} className="text-brand underline underline-offset-2">
                      Add the first one.
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}

function InlineForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: { name: string; default_unit: string | null; description: string | null }
  onSave: (fields: { name: string; default_unit: string; description: string }) => void
  onCancel: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [unit, setUnit] = useState(initial?.default_unit ?? '')
  const [desc, setDesc] = useState(initial?.description ?? '')
  const nameRef = useRef<HTMLInputElement>(null)

  useEffect(() => { nameRef.current?.focus() }, [])

  const inputCls = 'w-full rounded border bg-background px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-ring'

  return (
    <tr className="border-t bg-brand-muted/20">
      <td className="px-6 py-2">
        <input
          ref={nameRef}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. TiO₂"
          className={inputCls}
          onKeyDown={(e) => { if (e.key === 'Enter') onSave({ name, default_unit: unit, description: desc }) }}
        />
      </td>
      <td className="px-4 py-2">
        <input
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          placeholder="g"
          className={cn(inputCls, 'max-w-24')}
        />
      </td>
      <td className="px-4 py-2" colSpan={2}>
        <input
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          placeholder="Optional description"
          className={inputCls}
        />
      </td>
      <td className="px-6 py-2 text-right">
        <div className="flex items-center justify-end gap-1">
          <Button size="sm" onClick={() => onSave({ name, default_unit: unit, description: desc })} disabled={!name.trim()}>
            <Check className="h-3 w-3" />
            Save
          </Button>
          <Button size="sm" variant="outline" onClick={onCancel}>
            <X className="h-3 w-3" />
          </Button>
        </div>
      </td>
    </tr>
  )
}
