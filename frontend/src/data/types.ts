export type ProjectStatus = 'iterating' | 'converged' | 'flagged' | 'planning'

export interface IterationSummary {
  n: number
  best_objective: number | null
  status: string
  note?: string | null
}

export interface PortfolioProject {
  id: string
  name: string
  team: string
  owner: string
  status: ProjectStatus
  startedAt: string // ISO date
  endsAt: string // ISO date (planned)
  iteration: number
  maxIterations: number
  targetsMet: number
  targetsTotal: number
  domain: string
  iterations?: IterationSummary[]
}

export interface Target {
  property: string
  unit: string
  goal: string // raw DSL string, e.g. ">=0.92" or "[5,10]" or "+10%"
  reference?: string
}

export interface IngredientSpec {
  name: string
  unit: string
  min?: number
  max?: number
}

export interface PropertyMeasurement {
  name: string
  unit: string
  value: number
  sigma?: number // 1-sigma uncertainty (only for predictions)
}

export interface Formulation {
  id: string
  label: string
  kind: 'base' | 'tested' | 'proposed'
  iteration: number
  ingredients: Record<string, number> // name -> amount
  properties: PropertyMeasurement[]
  rationale?: string
  flagged?: boolean
}

export interface Iteration {
  n: number
  date: string
  candidates: number
  bestObjective: number
  status: 'done' | 'in-progress' | 'queued'
  note?: string
}

export interface ProjectDetail {
  id: string
  name: string
  team: string
  owner: string
  status: ProjectStatus
  domain: string
  startedAt: string
  endsAt: string
  iteration: number
  maxIterations: number
  ingredients: IngredientSpec[]
  targets: Target[]
  baseProducts: Formulation[]
  tested: Formulation[]
  proposed: Formulation[]
  iterations: Iteration[]
  flagNote?: string
}
