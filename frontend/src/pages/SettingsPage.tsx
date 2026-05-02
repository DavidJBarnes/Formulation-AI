import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Check, Loader2, Plus, ShieldCheck, Trash2, UserPlus, Users } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
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
  first_name: string | null
  last_name: string | null
  is_active: boolean
  is_admin: boolean
  abilities: string[]
}

// ---------------------------------------------------------------------------
// Settings page (admin or manage_users ability required)
// ---------------------------------------------------------------------------
export function SettingsPage() {
  const { user, hasAbility } = useAuth()

  const canAccess = user?.is_admin || hasAbility('manage_users')
  if (!canAccess) return <Navigate to="/" replace />

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Workspace configuration and user management.</p>
      </div>

      <UserManagement />
      {user?.is_admin && <UserAbilitiesMatrix />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// User management section
// ---------------------------------------------------------------------------
function UserManagement() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<UserWithAbilities[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<UserWithAbilities | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadUsers = async () => {
    try {
      const data = await apiFetch<UserWithAbilities[]>('/admin/users')
      setUsers(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const init = async () => {
      try {
        await loadUsers()
      } catch {
        // loadUsers() sets its own error state
      }
    }
    void init()
  }, [])

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await apiFetch(`/admin/users/${deleteTarget.id}`, { method: 'DELETE' })
      setUsers((prev) => prev.filter((u) => u.id !== deleteTarget.id))
      setDeleteTarget(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setDeleting(false)
    }
  }

  const displayName = (u: UserWithAbilities) => {
    if (u.first_name || u.last_name) return [u.first_name, u.last_name].filter(Boolean).join(' ') || u.email
    return u.full_name || u.email
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

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-brand" />
              Users
            </CardTitle>
            <CardDescription className="mt-1">
              Create and manage user accounts for this workspace.
            </CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={() => setShowCreateDialog(true)}>
            <UserPlus className="h-4 w-4" />
            Add user
          </Button>
        </CardHeader>

        {error && (
          <div className="mx-6 mb-4 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <CardContent className="overflow-x-auto">
          {users.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No users found. Click "Add user" to create one.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="pb-3 pr-6 text-left font-medium text-muted-foreground">Name</th>
                  <th className="pb-3 pr-6 text-left font-medium text-muted-foreground">Email</th>
                  <th className="pb-3 pr-6 text-center font-medium text-muted-foreground">Role</th>
                  <th className="pb-3 pr-6 text-center font-medium text-muted-foreground">Abilities</th>
                  <th className="pb-3 w-16 text-right font-medium text-muted-foreground" />
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const isSelf = u.id === currentUser?.id
                  return (
                    <tr key={u.id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                      <td className="py-3 pr-6 font-medium">
                        {displayName(u)}
                        {isSelf && (
                          <Badge variant="secondary" className="ml-2 text-[10px]">you</Badge>
                        )}
                      </td>
                      <td className="py-3 pr-6 text-muted-foreground">{u.email}</td>
                      <td className="py-3 pr-6 text-center">
                        {u.is_admin ? (
                          <Badge variant="default" className="text-[10px]">Admin</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">User</span>
                        )}
                      </td>
                      <td className="py-3 pr-6 text-center">
                        <span className="text-xs text-muted-foreground">
                          {u.abilities.length > 0 ? u.abilities.join(', ') : '—'}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                          disabled={isSelf}
                          onClick={() => setDeleteTarget(u)}
                          title={isSelf ? 'Cannot delete yourself' : 'Delete user'}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Create user dialog */}
      {showCreateDialog && (
        <CreateUserDialog
          open={showCreateDialog}
          onOpenChange={setShowCreateDialog}
          onCreated={(newUser) => {
            setUsers((prev) => [...prev, newUser])
            setShowCreateDialog(false)
          }}
        />
      )}

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete user</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete{' '}
              <span className="font-medium text-foreground">
                {deleteTarget ? displayName(deleteTarget) : ''}
              </span>
              ? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteTarget(null)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={() => void handleDelete()} disabled={deleting}>
              {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ---------------------------------------------------------------------------
// Create user dialog
// ---------------------------------------------------------------------------
function CreateUserDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  onCreated: (user: UserWithAbilities) => void
}) {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!email.trim() || !password.trim()) return
    setError(null)
    setSubmitting(true)
    try {
      const created = await apiFetch<UserWithAbilities>('/admin/users', {
        method: 'POST',
        body: {
          email: email.trim(),
          password: password,
          first_name: firstName.trim() || null,
          last_name: lastName.trim() || null,
          is_admin: isAdmin,
        },
      })
      onCreated(created)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create user')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add user</DialogTitle>
          <DialogDescription>
            Create a new user account for this workspace.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">First name</label>
              <Input
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="Jane"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Last name</label>
              <Input
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Smith"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Email / Username</label>
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="jane.smith@example.com"
              autoComplete="off"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Password</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min. 6 characters"
              autoComplete="new-password"
              onKeyDown={(e) => e.key === 'Enter' && void handleSubmit()}
            />
          </div>

          <label className="flex items-center gap-2.5 pt-1">
            <input
              type="checkbox"
              checked={isAdmin}
              onChange={(e) => setIsAdmin(e.target.checked)}
              className="h-4 w-4 rounded border-input text-brand focus:ring-brand"
            />
            <span className="text-sm">Admin user</span>
            <span className="text-xs text-muted-foreground">
              (grants all abilities implicitly)
            </span>
          </label>
        </div>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={() => void handleSubmit()} disabled={!email.trim() || !password.trim() || submitting}>
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Create user
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ---------------------------------------------------------------------------
// User × Ability matrix (admin only)
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
                          <span
                            className="inline-flex h-5 w-5 cursor-default items-center justify-center rounded"
                            title="Admin — all abilities granted implicitly"
                          >
                            <span className="inline-flex h-4 w-4 items-center justify-center rounded border-2 border-muted-foreground/40 bg-muted-foreground/20">
                              <Check className="h-2.5 w-2.5 text-muted-foreground/60" strokeWidth={3} />
                            </span>
                          </span>
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
