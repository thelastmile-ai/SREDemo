export interface Session {
  session_id: string
  username: string
  model: string
}

export interface PlanStep {
  id: string
  tool: string
  dependencies: string[]
  status: string
}

export interface StepResult {
  step_id: string
  tool: string
  status: string
  output: unknown
  timestamp?: number
}

export interface BudgetState {
  budget_used: number
  estimated_tokens: number
  context_limit: number
  compacted: boolean
  messages_evicted: number
  strategy: string
}

export interface EntityMap {
  [domain: string]: Record<string, unknown>
}

export interface ReportData {
  text: string
  metrics: {
    steps_executed?: number
    tunnels_reset?: number
    users_restored?: number
  }
}

export type NodeStatus = 'idle' | 'running' | 'done' | 'error'

export interface NodeEntry {
  node: string
  status: NodeStatus
  startedAt: number
  finishedAt?: number
}

export interface ClarificationState {
  question: string
}

export interface HistoryEntry {
  id: string
  action: string
  domain: string
  description: string
  outcome: 'COMPLETED' | 'FAILED'
  steps_count: number
  resolved_at: string
  duration_seconds: number
}

export type DemoPhase =
  | 'idle'
  | 'streaming'
  | 'hitl_pending'
  | 'clarifying'
  | 'executing'
  | 'complete'
  | 'error'
