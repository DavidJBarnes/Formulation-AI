import { cn } from '@/lib/utils'

interface LogoProps {
  className?: string
  variant?: 'mark' | 'wordmark'
}

export function Logo({ className, variant = 'wordmark' }: LogoProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden="true">
        <defs>
          <linearGradient id="fa-grad" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="hsl(221 83% 48%)" />
            <stop offset="100%" stopColor="hsl(262 70% 38%)" />
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="28" height="28" rx="8" fill="url(#fa-grad)" />
        <g fill="white" opacity="0.95">
          <circle cx="11" cy="11" r="2.1" />
          <circle cx="21" cy="11" r="2.1" />
          <circle cx="16" cy="20" r="2.1" />
          <path
            d="M11 11 L21 11 M11 11 L16 20 M21 11 L16 20"
            stroke="white"
            strokeWidth="1.4"
            opacity="0.7"
            fill="none"
          />
        </g>
      </svg>
      {variant === 'wordmark' && (
        <div className="flex flex-col leading-none">
          <span className="text-sm font-semibold tracking-tight text-foreground">
            Formulation<span className="text-brand">·AI</span>
          </span>
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Closed-loop optimization
          </span>
        </div>
      )}
    </div>
  )
}
