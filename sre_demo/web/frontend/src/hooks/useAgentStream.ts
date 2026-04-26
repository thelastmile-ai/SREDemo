import { useCallback, useRef, useState } from 'react'
import type {
  BudgetState,
  ClarificationState,
  DemoPhase,
  EntityMap,
  NodeEntry,
  PlanStep,
  ReportData,
  StepResult,
} from '../lib/types'

export interface AgentStreamState {
  phase: DemoPhase
  nodes: NodeEntry[]
  entities: EntityMap | null
  clarificationContext: string | null
  clarification: ClarificationState | null
  plan: PlanStep[] | null
  steps: StepResult[]
  budget: BudgetState | null
  report: ReportData | null
  error: string | null
  budgetHistory: { tokens: number; ts: number }[]
  fewShotHistoryId: string | null
}

const INITIAL: AgentStreamState = {
  phase: 'idle',
  nodes: [],
  entities: null,
  clarificationContext: null,
  clarification: null,
  plan: null,
  steps: [],
  budget: null,
  report: null,
  error: null,
  budgetHistory: [],
  fewShotHistoryId: null,
}

export function useAgentStream(sessionId: string | null) {
  const [state, setState] = useState<AgentStreamState>(INITIAL)
  const esRef = useRef<EventSource | null>(null)

  const connect = useCallback(() => {
    if (!sessionId) return
    if (esRef.current) esRef.current.close()

    setState((s: AgentStreamState) => ({ ...s, phase: 'streaming' }))
    const es = new EventSource(`/api/stream?session_id=${sessionId}`)
    esRef.current = es

    const handle = (eventName: string, data: unknown) => {
      const d = data as Record<string, unknown>
      setState((prev: AgentStreamState) => {
        switch (eventName) {
          case 'node_start':
            return {
              ...prev,
              nodes: [
                ...prev.nodes,
                { node: d.node as string, status: 'running' as const, startedAt: Date.now() },
              ],
            }

          case 'node_done':
            return {
              ...prev,
              nodes: prev.nodes.map((n: NodeEntry) =>
                n.node === (d.node as string) && n.status === 'running'
                  ? { ...n, status: 'done' as const, finishedAt: Date.now() }
                  : n,
              ),
            }

          case 'clarification_needed':
            return {
              ...prev,
              phase: 'clarifying' as const,
              clarification: { question: d.question as string },
            }

          case 'entities':
            return {
              ...prev,
              phase: prev.phase === 'clarifying' ? 'streaming' : prev.phase,
              entities: d.entities as EntityMap,
              clarification: null,
              clarificationContext: (d.clarification_context as string) ?? prev.clarificationContext,
            }

          case 'plan_ready':
            return { ...prev, phase: 'hitl_pending' as const, plan: d.steps as PlanStep[] }

          case 'step_result': {
            const result: StepResult = {
              step_id: d.step_id as string,
              tool: d.tool as string,
              status: d.status as string,
              output: d.output,
              timestamp: Date.now(),
            }
            return { ...prev, phase: 'executing' as const, steps: [...prev.steps, result] }
          }

          case 'budget': {
            const b = d as unknown as BudgetState
            return {
              ...prev,
              budget: b,
              budgetHistory: [...prev.budgetHistory, { tokens: b.estimated_tokens, ts: Date.now() }],
            }
          }

          case 'report':
            return { ...prev, phase: 'complete' as const, report: d as unknown as ReportData }

          case 'few_shot':
            return { ...prev, fewShotHistoryId: d.history_id as string }

          case 'error':
            return { ...prev, phase: 'error' as const, error: d.message as string }

          default:
            return prev
        }
      })
    }

    const eventTypes = [
      'node_start', 'node_done', 'clarification_needed', 'entities',
      'plan_ready', 'step_result', 'budget', 'report', 'error', 'few_shot',
    ]
    for (const name of eventTypes) {
      es.addEventListener(name, (e: MessageEvent) => {
        try { handle(name, JSON.parse(e.data)) } catch { /* ignore parse errors */ }
      })
    }

    es.onerror = () => {
      setState((s: AgentStreamState) =>
        s.phase !== 'complete' && s.phase !== 'error'
          ? { ...s, phase: 'error', error: 'SSE connection lost' }
          : s,
      )
    }
  }, [sessionId])

  const disconnect = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  const reset = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
    setState(INITIAL)
  }, [])

  return { state, connect, disconnect, reset }
}
