import { Activity, AlertTriangle, CheckCircle2, CircleDashed } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { ProjectStatus } from '@/data/types'

const VARIANT: Record<ProjectStatus, { label: string; variant: 'active' | 'archived' | 'danger' | 'muted'; icon: typeof Activity }> = {
  iterating: { label: 'Iterating', variant: 'active', icon: Activity },
  converged: { label: 'Converged', variant: 'active', icon: CheckCircle2 },
  flagged: { label: 'Data flag', variant: 'danger', icon: AlertTriangle },
  planning: { label: 'Planning', variant: 'muted', icon: CircleDashed },
}

export function StatusBadge({ status }: { status: ProjectStatus }) {
  const v = VARIANT[status]
  const Icon = v.icon
  // converged should look "done", not "in-progress" — override styling slightly
  const variant = status === 'converged' ? 'archived' : v.variant
  return (
    <Badge variant={variant} className="gap-1.5">
      <Icon className="h-3 w-3" />
      {v.label}
    </Badge>
  )
}
