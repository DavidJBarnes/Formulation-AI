import { useAuth } from '@/lib/auth'

export function HomePage() {
  const { user, logout } = useAuth()
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-foreground">Formulation-AI</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Signed in as <span className="font-medium text-foreground">{user?.email}</span>
        </p>
      </div>
      <button
        type="button"
        onClick={logout}
        className="rounded-md border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted"
      >
        Sign out
      </button>
    </div>
  )
}
