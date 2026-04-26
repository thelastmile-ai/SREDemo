import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Clock, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../lib/api'
import type { HistoryEntry } from '../lib/types'
import HistoryCard from './HistoryCard'

interface PlanHistoryPanelProps {
  fewShotHistoryId: string | null
  refreshTrigger: number
}

export default function PlanHistoryPanel({
  fewShotHistoryId,
  refreshTrigger,
}: PlanHistoryPanelProps) {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    api.history().then(setEntries).catch(() => {})
  }, [refreshTrigger])

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-[#0d1117] border border-[#1c2333] rounded-xl flex flex-col overflow-hidden h-full"
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setCollapsed(x => !x)}
        className="flex items-center justify-between px-4 py-3 border-b border-[#1c2333]
                   hover:bg-white/[0.02] transition-colors flex-shrink-0 w-full text-left"
      >
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-purple-500/15 flex items-center justify-center">
            <Clock className="w-3 h-3 text-purple-400" />
          </div>
          <span className="text-xs font-semibold text-[#8b949e] uppercase tracking-widest">
            Plan History
          </span>
          {entries.length > 0 && (
            <span className="text-[10px] bg-[#161b22] border border-[#1c2333] rounded-full px-1.5 py-0.5 text-[#484f58]">
              {entries.length}
            </span>
          )}
        </div>
        {collapsed
          ? <ChevronDown className="w-3.5 h-3.5 text-[#484f58]" />
          : <ChevronUp className="w-3.5 h-3.5 text-[#484f58]" />}
      </button>

      {/* Entries */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {entries.length === 0 ? (
            <p className="text-xs text-[#484f58] text-center py-6">No history yet</p>
          ) : (
            entries.map(entry => (
              <HistoryCard
                key={entry.id}
                entry={entry}
                fewShotUsed={entry.id === fewShotHistoryId}
              />
            ))
          )}
        </div>
      )}
    </motion.div>
  )
}
