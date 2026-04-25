import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Beaker,
  Compass,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  Settings,
  Upload,
  UserRound,
} from 'lucide-react'
import { Logo } from '@/components/Logo'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth'

const nav = [
  { to: '/', label: 'Portfolio', icon: LayoutDashboard, end: true },
  { to: '/projects/paint-low-voc', label: 'Active Project', icon: Beaker },
  { to: '/upload', label: 'New Project', icon: Upload },
  { to: '/explore', label: 'Explore', icon: Compass, disabled: true },
]

const secondaryNav = [
  { to: '/settings', label: 'Settings', icon: Settings, disabled: true },
  { to: '/help', label: 'Help', icon: HelpCircle, disabled: true },
]

export function AppShell() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const displayName = user?.full_name || user?.email?.split('@')[0] || 'Researcher'
  const initials = displayName
    .split(/[\s.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? '')
    .join('') || 'R'

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-screen w-full overflow-hidden bg-background">
        {/* Sidebar */}
        <aside className="hidden w-60 shrink-0 flex-col border-r bg-card md:flex">
          <div className="flex h-16 items-center border-b px-5">
            <Logo />
          </div>
          <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4">
            <p className="px-3 pb-1.5 pt-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Workspace
            </p>
            {nav.map((item) => (
              <NavItem key={item.to} {...item} />
            ))}
            <p className="mt-6 px-3 pb-1.5 pt-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              System
            </p>
            {secondaryNav.map((item) => (
              <NavItem key={item.to} {...item} />
            ))}
          </nav>
          <div className="border-t p-3">
            <div className="rounded-lg bg-brand-muted p-3">
              <div className="text-xs font-semibold text-brand">Phase 1 · POC</div>
              <p className="mt-1 text-xs leading-snug text-brand/80">
                LLM-only proposal engine. Bayesian optimizer slots in for Phase 2.
              </p>
            </div>
          </div>
        </aside>

        {/* Main */}
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-16 shrink-0 items-center gap-4 border-b bg-card px-6">
            <div className="flex flex-1 items-center gap-3 text-sm text-muted-foreground">
              <span className="hidden md:inline">
                Closed-loop optimization · DOE inner loop 3→6 · {new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            </div>
            <Badge variant="muted" className="hidden md:inline-flex">
              v0.1 · preview
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center gap-2 rounded-full p-1 pl-2 hover:bg-muted">
                <span className="hidden text-right text-xs leading-tight md:block">
                  <span className="block font-medium text-foreground">{displayName}</span>
                  <span className="block text-muted-foreground">{user?.email}</span>
                </span>
                <Avatar className="h-8 w-8">
                  <AvatarFallback>{initials}</AvatarFallback>
                </Avatar>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>Signed in</DropdownMenuLabel>
                <DropdownMenuItem className="cursor-default">
                  <UserRound className="h-4 w-4" />
                  <div className="flex flex-col">
                    <span className="text-sm">{displayName}</span>
                    <span className="text-xs text-muted-foreground">{user?.email}</span>
                  </div>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onSelect={() => {
                    logout()
                    navigate('/login')
                  }}
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </header>

          <main className="flex-1 overflow-y-auto scrollbar-thin">
            <Outlet />
          </main>
        </div>
      </div>
    </TooltipProvider>
  )
}

function NavItem({
  to,
  label,
  icon: Icon,
  end,
  disabled,
}: {
  to: string
  label: string
  icon: typeof Beaker
  end?: boolean
  disabled?: boolean
}) {
  if (disabled) {
    return (
      <span className={cn('flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground/60 cursor-not-allowed')}>
        <Icon className="h-4 w-4" />
        {label}
        <Badge variant="muted" className="ml-auto text-[9px]">
          soon
        </Badge>
      </span>
    )
  }
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-brand-muted text-brand'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground',
        )
      }
    >
      <Icon className="h-4 w-4" />
      {label}
    </NavLink>
  )
}
