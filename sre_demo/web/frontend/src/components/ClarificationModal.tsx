import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HelpCircle, Send } from 'lucide-react'

interface ClarificationModalProps {
  question: string
  onSubmit: (answer: string) => Promise<void>
}

export default function ClarificationModal({ question, onSubmit }: ClarificationModalProps) {
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)

  const canSubmit = answer.trim().length >= 5 && !loading

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setLoading(true)
    try {
      await onSubmit(answer.trim())
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 16 }}
          transition={{ duration: 0.25 }}
          className="bg-[#0d1117] border border-amber-500/30 rounded-2xl p-6 shadow-2xl w-full max-w-lg mx-4"
        >
          {/* Header */}
          <div className="flex items-start gap-3 mb-5">
            <div className="w-9 h-9 rounded-lg bg-amber-500/15 flex items-center justify-center flex-shrink-0 mt-0.5">
              <HelpCircle className="w-4.5 h-4.5 text-amber-400" />
            </div>
            <div>
              <p className="text-[10px] text-amber-400/70 uppercase tracking-widest mb-1">
                Agent needs clarification
              </p>
              <h3 className="text-white font-semibold text-sm leading-snug">
                {question}
              </h3>
            </div>
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="space-y-3">
            <textarea
              autoFocus
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              placeholder="Type your answer…"
              rows={3}
              className="w-full bg-[#161b22] border border-[#1c2333] rounded-xl px-4 py-3
                         text-sm text-[#e6edf3] placeholder-[#484f58] resize-none
                         focus:outline-none focus:border-amber-500/50 focus:ring-1
                         focus:ring-amber-500/20 transition-colors"
              onKeyDown={e => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e as unknown as React.FormEvent)
              }}
            />

            <div className="flex items-center justify-between">
              <span className="text-xs text-[#484f58]">
                {answer.length > 0 && answer.trim().length < 5
                  ? `${5 - answer.trim().length} more characters needed`
                  : answer.trim().length >= 5 ? '⌘↵ to submit' : ''}
              </span>

              <motion.button
                type="submit"
                disabled={!canSubmit}
                whileHover={canSubmit ? { scale: 1.02 } : {}}
                whileTap={canSubmit ? { scale: 0.98 } : {}}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                           transition-all duration-200
                           ${canSubmit
                             ? 'bg-amber-500 hover:bg-amber-400 text-black cursor-pointer'
                             : 'bg-[#161b22] text-[#484f58] border border-[#1c2333] cursor-not-allowed'
                           }`}
              >
                {loading ? (
                  <span className="w-3.5 h-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
                )}
                {loading ? 'Submitting…' : 'Submit'}
              </motion.button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
