import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'

interface IncidentPanelProps {
  message: string
}

export default function IncidentPanel({ message }: IncidentPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-[#0d1117] border border-red-500/30 rounded-xl p-5 shadow-lg"
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 rounded-lg bg-red-500/15 flex items-center justify-center flex-shrink-0">
          <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-red-400 bg-red-500/15 px-2 py-0.5 rounded border border-red-500/30">
            ACTIVE
          </span>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
          </span>
        </div>
      </div>

      <p className="text-[10px] text-[#8b949e] uppercase tracking-widest mb-2">Incident</p>
      <p className="text-sm text-[#e6edf3] leading-relaxed">
        {message || '—'}
      </p>
    </motion.div>
  )
}
