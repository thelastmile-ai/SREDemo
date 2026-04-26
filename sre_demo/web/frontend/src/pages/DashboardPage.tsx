import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { Terminal, LogOut, Cpu } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { useSession } from '../hooks/useSession'
import { useAgentStream } from '../hooks/useAgentStream'
import { api } from '../lib/api'

import BudgetGauge from '../components/BudgetGauge'
import IncidentPanel from '../components/IncidentPanel'
import IncidentInput from '../components/IncidentInput'
import ActivityFeed from '../components/ActivityFeed'
import EntityCard from '../components/EntityCard'
import HitlModal from '../components/HitlModal'
import ClarificationModal from '../components/ClarificationModal'
import ExecutionFeed from '../components/ExecutionFeed'
import ReportCard from '../components/ReportCard'
import PlanTable from '../components/PlanTable'
import PlanHistoryPanel from '../components/PlanHistoryPanel'
import WarningBanner from '../components/WarningBanner'
import CompactionBanner from '../components/CompactionBanner'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { session, clearSession } = useSession()
  const { state, connect } = useAgentStream(session?.session_id ?? null)
  const startedAt = useRef(Date.now())
  const prevPhase = useRef(state.phase)

  const [incidentMessage, setIncidentMessage] = useState('')
  const [historyRefreshCount, setHistoryRefreshCount] = useState(0)

  // Compaction banner state
  const [showCompaction, setShowCompaction] = useState(false)
  const [compactionData, setCompactionData] = useState({ evicted: 0, headroom: 0 })
  const prevCompacted = useRef(false)

  // Phase change toasts (excluding compaction — handled by banner)
  const prevBudgetPct = useRef(0)
  useEffect(() => {
    const prev = prevPhase.current
    const curr = state.phase
    prevPhase.current = curr

    if (curr === 'hitl_pending' && prev !== 'hitl_pending') {
      toast('⚡ Plan ready — awaiting your approval', { duration: 4000 })
    }
    if (curr === 'complete' && prev !== 'complete') {
      toast.success('Incident resolved! Report ready.', { duration: 5000 })
      setHistoryRefreshCount(c => c + 1)
    }
    if (curr === 'error') {
      toast.error(state.error ?? 'Agent error', { duration: 6000 })
    }
  }, [state.phase, state.error])

  // Compaction banner (replaces toast)
  useEffect(() => {
    if (!state.budget) return
    const { compacted, messages_evicted, estimated_tokens } = state.budget

    if (compacted && !prevCompacted.current) {
      const headroomPct = Math.round((messages_evicted / Math.max(1, messages_evicted + estimated_tokens / 4)) * 100)
      setCompactionData({ evicted: messages_evicted, headroom: Math.min(headroomPct, 99) })
      setShowCompaction(true)
      const t = setTimeout(() => setShowCompaction(false), 4000)
      prevCompacted.current = true
      return () => clearTimeout(t)
    }
    if (!compacted) {
      prevCompacted.current = false
    }
    prevBudgetPct.current = state.budget.budget_used
  }, [state.budget])

  const handleStart = async (message: string) => {
    if (!session) return
    setIncidentMessage(message)
    startedAt.current = Date.now()
    await api.start(session.session_id, message)
    connect()
  }

  const handleApprove = async () => {
    if (!session) return
    await api.approve(session.session_id, 'approved')
    toast.success('Plan approved — execution starting…')
  }

  const handleRevise = async (feedback: string) => {
    if (!session) return
    await api.approve(session.session_id, feedback)
    toast('Plan revision submitted — re-planning…')
  }

  const handleClarify = async (answer: string) => {
    if (!session) return
    await api.clarify(session.session_id, answer)
  }

  const handleLogout = () => {
    clearSession()
    navigate('/')
  }

  const isRunning = state.phase !== 'idle'
  const showHitl = state.phase === 'hitl_pending'
  const showClarification = state.phase === 'clarifying' && !!state.clarification
  const showPlan = state.plan && !showHitl && state.phase !== 'executing' && state.phase !== 'complete'
  const showExecution = state.steps.length > 0
  const showReport = state.phase === 'complete' && state.report

  const fewShotHistoryId = state.fewShotHistoryId

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-[#080b10] flex flex-col"
    >
      {/* Header */}
      <header className="flex-shrink-0 bg-[#0d1117] border-b border-[#1c2333] px-6 py-3 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center">
            <Terminal className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-sm font-bold text-white">
            AgentCore
            <span className="text-purple-400 ml-1">·</span>
            <span className="text-[#8b949e] font-normal ml-1">SRE Demo</span>
          </span>
        </div>

        {session && (
          <div className="hidden sm:flex items-center gap-2 bg-[#161b22] border border-[#1c2333] rounded-full px-3 py-1">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-xs text-[#8b949e] font-mono">{session.session_id.slice(0, 8)}</span>
          </div>
        )}

        <div className="flex items-center gap-2 ml-auto">
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-[#8b949e] bg-[#161b22] border border-[#1c2333] rounded-full px-3 py-1">
            <Cpu className="w-3 h-3 text-purple-400" />
            {session?.model ?? 'claude-sonnet-4-6'}
          </div>

          <div className={`text-[10px] uppercase tracking-widest rounded-full px-3 py-1 border font-medium ${
            state.phase === 'complete'     ? 'text-green-400 bg-green-500/10 border-green-500/20'
            : state.phase === 'error'      ? 'text-red-400 bg-red-500/10 border-red-500/20'
            : state.phase === 'hitl_pending' ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
            : state.phase === 'clarifying'   ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
            : state.phase === 'idle'         ? 'text-[#484f58] bg-[#161b22] border-[#1c2333]'
            : 'text-purple-400 bg-purple-500/10 border-purple-500/20'
          }`}>
            {state.phase === 'idle' ? 'Ready' : state.phase.replace('_', ' ')}
          </div>

          <BudgetGauge budget={state.budget} history={state.budgetHistory} />

          <button
            onClick={handleLogout}
            className="p-2 rounded-lg text-[#8b949e] hover:text-white hover:bg-[#161b22] transition-colors"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Warning banner — slides in below header when budget ≥ 70% */}
      <WarningBanner budgetUsed={state.budget?.budget_used ?? 0} />

      {/* Compaction banner — full-width animated strip */}
      <CompactionBanner
        visible={showCompaction}
        messagesEvicted={compactionData.evicted}
        headroomPct={compactionData.headroom}
      />

      {/* Main content */}
      <main className="flex-1 overflow-hidden p-4 flex flex-col gap-4">
        <AnimatePresence mode="wait">
          {!isRunning ? (
            /* ── Idle: full-area incident input ─────────────────────────── */
            <motion.div
              key="incident-input"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex-1 flex gap-4"
            >
              {/* Incident input (center) */}
              <div className="flex-1 min-w-0">
                <IncidentInput onSubmit={handleStart} />
              </div>

              {/* History panel (right rail) */}
              <div className="w-72 flex-shrink-0">
                <PlanHistoryPanel
                  fewShotHistoryId={null}
                  refreshTrigger={historyRefreshCount}
                />
              </div>
            </motion.div>
          ) : (
            /* ── Running: live dashboard ────────────────────────────────── */
            <motion.div
              key="dashboard"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex-1 flex flex-col gap-4 overflow-hidden"
            >
              {/* Top row */}
              <div className="flex gap-4 min-h-0" style={{ height: 'min(380px, 40vh)' }}>
                {/* Left column */}
                <div className="w-72 flex-shrink-0 flex flex-col gap-3 overflow-y-auto">
                  <IncidentPanel message={incidentMessage} />
                  <EntityCard entities={state.entities} />
                  {state.clarificationContext && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3"
                    >
                      <p className="text-[10px] text-amber-400/70 uppercase tracking-widest mb-1">Clarification</p>
                      <p className="text-xs text-[#e6edf3]">{state.clarificationContext}</p>
                    </motion.div>
                  )}
                </div>

                {/* Center — activity feed */}
                <div className="flex-1 min-w-0">
                  <ActivityFeed nodes={state.nodes} />
                </div>

                {/* Right — history panel */}
                <div className="w-64 flex-shrink-0">
                  <PlanHistoryPanel
                    fewShotHistoryId={fewShotHistoryId}
                    refreshTrigger={historyRefreshCount}
                  />
                </div>
              </div>

              {/* Bottom area */}
              <div className="flex-1 overflow-y-auto space-y-4 pb-4">
                {showPlan && state.plan && (
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-[#0d1117] border border-[#1c2333] rounded-xl p-5"
                  >
                    <PlanTable steps={state.plan} />
                  </motion.div>
                )}
                {showExecution && <ExecutionFeed steps={state.steps} />}
                {showReport && state.report && (
                  <ReportCard report={state.report} startedAt={startedAt.current} />
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* HITL modals — block entire UI */}
      {showHitl && state.plan && (
        <HitlModal steps={state.plan} onApprove={handleApprove} onRevise={handleRevise} />
      )}
      {showClarification && state.clarification && (
        <ClarificationModal
          question={state.clarification.question}
          onSubmit={handleClarify}
        />
      )}
    </motion.div>
  )
}
