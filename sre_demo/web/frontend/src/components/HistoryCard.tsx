import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import type { HistoryEntry } from '../lib/types'

interface HistoryCardProps {
  entry: HistoryEntry
  fewShotUsed: boolean
}

function timeAgo(isoStr: string): string {
  const diff = Date.now() - new Date(isoStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 2) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

const DOMAIN_COLORS: Record<string, string> = {
  networking: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  database:   'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  kubernetes: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
  security:   'text-orange-400 bg-orange-500/10 border-orange-500/20',
}

export default function HistoryCard({ entry, fewShotUsed }: HistoryCardProps) {
  const [expanded, setExpanded] = useState(false)
  const domainColor = DOMAIN_COLORS[entry.domain] ?? 'text-[#8b949e] bg-[#161b22] border-[#1c2333]'
  const isCompleted = entry.outcome === 'COMPLETED'

  return (
    <motion.div
      layout
      className={`bg-[#0d1117] border rounded-xl overflow-hidden transition-colors
                  ${fewShotUsed ? 'border-purple-500/40' : 'border-[#1c2333]'}`}
    >
      {/* Few-shot badge */}
      <AnimatePresence>
        {fewShotUsed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-purple-500/10 border-b border-purple-500/20 px-3 py-1.5
                       flex items-center gap-1.5"
          >
            <Sparkles className="w-3 h-3 text-purple-400" />
            <span className="text-[10px] text-purple-400 font-medium uppercase tracking-widest">
              Few-shot used by agent
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main row */}
      <button
        type="button"
        onClick={() => setExpanded(x => !x)}
        className="w-full text-left px-3 py-3 flex items-start gap-2.5 hover:bg-white/[0.02] transition-colors"
      >
        {/* Outcome icon */}
        <div className="mt-0.5 flex-shrink-0">
          {isCompleted
            ? <CheckCircle2 className="w-4 h-4 text-green-400" />
            : <XCircle className="w-4 h-4 text-red-400" />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1 flex-wrap">
            <span className={`text-[10px] border rounded px-1.5 py-0.5 font-medium ${domainColor}`}>
              {entry.domain}
            </span>
            <span className="text-[10px] text-[#484f58]">{timeAgo(entry.resolved_at)}</span>
          </div>
          <p className="text-xs text-[#e6edf3] leading-snug line-clamp-2">
            {entry.description}
          </p>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-[10px] text-[#484f58]">{entry.steps_count} steps</span>
            <span className="text-[10px] text-[#484f58]">·</span>
            <span className="text-[10px] text-[#484f58]">{entry.duration_seconds}s</span>
          </div>
        </div>

        {/* Expand chevron */}
        <div className="flex-shrink-0 text-[#484f58] mt-0.5">
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </button>

      {/* Expanded detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-[#1c2333] px-3 py-2"
          >
            <p className="text-[10px] text-[#8b949e] uppercase tracking-widest mb-1">Action</p>
            <p className="text-xs font-mono text-purple-400">{entry.action}</p>
            <p className="text-[10px] text-[#8b949e] uppercase tracking-widest mt-2 mb-1">Resolved</p>
            <p className="text-xs text-[#8b949e]">{new Date(entry.resolved_at).toLocaleString()}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
