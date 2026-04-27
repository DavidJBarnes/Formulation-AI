import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Loader2, Plus, ShieldCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { apiFetch } from '@/lib/api'
import { useAuth } from '@/lib/auth'

// ---------------------------------------------------------------------------
// API types
// ---------------------------------------------------------------------------
interface AbilityOut {
  key: string
  description: string | null
}

interface UserWithAbilities {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_admin: boolean
  abilities: string[]
}

// ---------------------------------------------------------------------------
// Settings page (admin only)
// ---------------------------------------------------------------------------
export function SettingsPage() {
  const { user } = useAuth()

  if (!user?.is_admin) return <Navigate to="/" replace />

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Admin configuration for this workspace.</p>
      </div>
      <UserAbilitiesMatrix />
    </div>
  )
}

// ---------------------------------------------------------------------------
// User × Ability matrix
// ---------------------------------------------------------------------------
function UserAbilitiesMatrix() {
  const [users, setUsers] = useState<UserWithAbilities[]>([])
  const [abilities, setAbilities] = useState<AbilityOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toggling, setToggling] = useState<string | null>(null) // "userId:key"
  const [addingAbility, setAddingAbility] = useState(false)
  const [newKey, setNewKey] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [addError, setAddError] = useState<string | null>(null)

  const load = async () => {
    try {
      const [u, a] = await Promise.all([
        apiFetch<UserWithAbilities[]>('/admin/users'),
        apiFetch<AbilityOut[]>('/admin/abilities'),
      ])
      setUsers(u)
      setAbilities(a)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const init = async () => {
      try {
        await load()
      } catch {
        // load() sets its own error state
      }
    }
    void init()
  }, [])

  const toggle = async (userId: string, abilityKey: string, currentlyGranted: boolean) => {
    const id = `${userId}:${abilityKey}`
    setToggling(id)
    try {
      if (currentlyGranted) {
        await apiFetch(`/admin/users/${userId}/abilities/${abilityKey}`, { method: 'DELETE' })
      } else {
        await apiFetch(`/admin/users/${userId}/abilities/${abilityKey}`, { method: 'POST' })
      }
      setUsers((prev) =>
        prev.map((u) => {
          if (u.id !== userId) return u
          return {
            ...u,
            abilities: currentlyGranted
              ? u.abilities.filter((k) => k !== abilityKey)
              : [...u.abilities, abilityKey],
          }
        }),
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Toggle failed')
    } finally {
      setToggling(null)
    }
  }

  const handleAddAbility = async () => {
    const key = newKey.trim().toLowerCase().replace(/\s+/g, '_')
    if (!key) return
    setAddError(null)
    try {
      const created = await apiFetch<AbilityOut>('/admin/abilities', {
        method: 'POST',
        body: { key, description: newDesc.trim() || null },
      })
      setAbilities((prev) => [...prev, created])
      setNewKey('')
      setNewDesc('')
      setAddingAbility(false)
    } catch (e) {
      setAddError(e instanceof Error ? e.message : 'Failed to add ability')
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-destructive">{error}</CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-brand" />
            User Abilities
          </CardTitle>
          <CardDescription className="mt-1">
            Check a cell to grant an ability to a user. Admins have all abilities implicitly.
          </CardDescription>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setAddingAbility((v) => !v)}
        >
          <Plus className="h-4 w-4" />
          Add ability
        </Button>
      </CardHeader>

      {addingAbility && (
        <div className="mx-6 mb-4 rounded-lg border bg-muted/40 p-4">
          <p className="mb-3 text-sm font-medium">New ability</p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              className="flex-1 rounded-md border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
              placeholder="ability_key (e.g. run_iterations)"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void handleAddAbility()}
            />
            <input
              className="flex-1 rounded-md border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
              placeholder="Description (optional)"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void handleAddAbility()}
            />
            <Button size="sm" onClick={() => void handleAddAbility()} disabled={!newKey.trim()}>
              Save
            </Button>
            <Button size="sm" variant="ghost" onClick={() => { setAddingAbility(false); setAddError(null) }}>
              Cancel
            </Button>
          </div>
          {addError && <p className="mt-2 text-xs text-destructive">{addError}</p>}
        </div>
      )}

      <CardContent className="overflow-x-auto">
        {abilities.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No abilities defined yet. Click "Add ability" to create one.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="pb-3 pr-6 text-left font-medium text-muted-foreground">User</th>
                {abilities.map((a) => (
                  <th key={a.key} className="pb-3 px-4 text-center font-medium text-muted-foreground" title={a.description ?? ''}>
                    <span className="block max-w-[120px] truncate">{a.key}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                  <td className="py-3 pr-6">
                    <div className="font-medium">{u.full_name || u.email}</div>
                    {u.full_name && (
                      <div className="text-xs text-muted-foreground">{u.email}</div>
                    )}
                    {u.is_admin && (
                      <Badge variant="secondary" className="mt-0.5 text-[10px]">admin</Badge>
                    )}
                  </td>
                  {abilities.map((a) => {
                    const granted = u.abilities.includes(a.key)
                    const cellId = `${u.id}:${a.key}`
                    const busy = toggling === cellId
                    return (
                      <td key={a.key} className="px-4 py-3 text-center">
                        {u.is_admin ? (
                          <span className="text-muted-foreground/40" title="Admins have all abilities">—</span>
                        ) : (
                          <button
                            onClick={() => void toggle(u.id, a.key, granted)}
                            disabled={busy}
                            className="inline-flex h-5 w-5 items-center justify-center rounded"
                            aria-label={`${granted ? 'Revoke' : 'Grant'} ${a.key} for ${u.email}`}
                          >
                            {busy ? (
                              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                            ) : (
                              <span
                                className={`h-4 w-4 rounded border-2 transition-colors ${
                                  granted
                                    ? 'border-brand bg-brand'
                                    : 'border-muted-foreground/40 bg-transparent hover:border-brand'
                                }`}
                              />
                            )}
                          </button>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  )
}
