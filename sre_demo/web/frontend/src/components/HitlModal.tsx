import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, MessageSquare, Loader2, AlertTriangle } from 'lucide-react'
import PlanTable from './PlanTable'
import type { PlanStep } from '../lib/types'

interface Props {
  steps: PlanStep[]
  onApprove: () => Promise<void>
  onRevise: (feedback: string) => Promise<void>
}

export default function HitlModal({ steps, onApprove, onRevise }: Props) {
  const [mode, setMode] = useState<'review' | 'revise'>('review')
  const [feedback, setFeedback] = useState('')
  const [loading, setLoading] = useState(false)

  const handleApprove = async () => {
    setLoading(true)
    await onApprove()
  }

  const handleRevise = async () => {
    if (!feedback.trim()) return
    setLoading(true)
    await onRevise(feedback)
  }

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.92, y: 24 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 24 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="bg-[#0d1117] border border-[#1c2333] rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col"
          style={{ boxShadow: '0 0 0 1px rgba(168,85,247,0.2), 0 25px 60px rgba(0,0,0,0.8)' }}
        >
          {/* Header */}
          <div className="px-7 py-5 border-b border-[#1c2333] flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-amber-500/15 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h2 className="text-white font-bold text-lg leading-tight">
                ⚡ Human Approval Required
              </h2>
              <p className="text-[#8b949e] text-sm mt-0.5">
                Review the remediation plan before execution proceeds
              </p>
            </div>
          </div>

          {/* Body — scrollable */}
          <div className="flex-1 overflow-y-auto px-7 py-5">
            <PlanTable steps={steps} />

            {/* Revision text area */}
            <AnimatePresence>
              {mode === 'revise' && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-5"
                >
                  <label className="block text-xs text-[#8b949e] uppercase tracking-widest mb-2">
                    Revision Feedback
                  </label>
                  <textarea
                    value={feedback}
                    onChange={e => setFeedback(e.target.value)}
                    placeholder="Describe changes to the plan (e.g. 'Skip PagerDuty steps, focus on tunnel reset only')…"
                    rows={4}
                    className="w-full px-4 py-3 bg-[#161b22] border border-[#30363d] rounded-lg text-sm text-white placeholder-[#484f58] outline-none resize-none
                      focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all"
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Footer CTAs */}
          <div className="px-7 py-5 border-t border-[#1c2333] flex gap-3">
            {mode === 'review' ? (
              <>
                <button
                  onClick={handleApprove}
                  disabled={loading}
                  className="flex-1 py-3 rounded-xl font-semibold text-sm text-white transition-all duration-200
                    bg-gradient-to-r from-green-600 to-emerald-600
                    hover:from-green-500 hover:to-emerald-500 hover:shadow-lg hover:shadow-green-900/40 hover:scale-[1.02]
                    active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:scale-100
                    flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Zap className="w-4 h-4" />
                  )}
                  Approve & Execute
                </button>
                <button
                  onClick={() => setMode('revise')}
                  disabled={loading}
                  className="px-6 py-3 rounded-xl font-semibold text-sm text-[#8b949e] bg-[#161b22] border border-[#1c2333]
                    hover:bg-[#1c2333] hover:text-white transition-all duration-200 flex items-center gap-2
                    disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  <MessageSquare className="w-4 h-4" />
                  Revise Plan
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleRevise}
                  disabled={loading || !feedback.trim()}
                  className="flex-1 py-3 rounded-xl font-semibold text-sm text-white transition-all duration-200
                    bg-gradient-to-r from-purple-600 to-indigo-600
                    hover:from-purple-500 hover:to-indigo-500 hover:shadow-lg hover:shadow-purple-900/40 hover:scale-[1.02]
                    active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:scale-100
                    flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <MessageSquare className="w-4 h-4" />
                  )}
                  Submit Revision
                </button>
                <button
                  onClick={() => setMode('review')}
                  disabled={loading}
                  className="px-6 py-3 rounded-xl font-semibold text-sm text-[#8b949e] bg-[#161b22] border border-[#1c2333]
                    hover:bg-[#1c2333] hover:text-white transition-all duration-200
                    disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  Back
                </button>
              </>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
