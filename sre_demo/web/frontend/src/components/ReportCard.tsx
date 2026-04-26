import { motion } from 'framer-motion'
import { CheckCircle2, Clock, Activity, Users, Network, Download } from 'lucide-react'
import type { ReportData } from '../lib/types'

interface Props {
  report: ReportData
  startedAt: number
}

function elapsed(ms: number): string {
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return `${m}m ${s % 60}s`
}

export default function ReportCard({ report, startedAt }: Props) {
  const duration = Date.now() - startedAt
  const { steps_executed = 0, tunnels_reset = 0, users_restored = 0 } = report.metrics

  const handleDownload = () => {
    const blob = new Blob([report.text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `incident-report-${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="bg-[#0d1117] border border-green-500/30 rounded-xl p-6 border-glow-green"
    >
      {/* Title */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-green-500/15 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h2 className="text-white font-bold text-lg">Incident Resolved ✓</h2>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Clock className="w-3 h-3 text-[#8b949e]" />
              <span className="text-xs text-[#8b949e]">Resolved in {elapsed(duration)}</span>
            </div>
          </div>
        </div>
        <button
          onClick={handleDownload}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium text-[#8b949e] bg-[#161b22] border border-[#1c2333]
            hover:bg-[#1c2333] hover:text-white transition-all"
        >
          <Download className="w-3.5 h-3.5" />
          Download Report
        </button>
      </div>

      {/* Metric chips */}
      <div className="flex gap-3 flex-wrap mb-5">
        {[
          { icon: <Activity className="w-3.5 h-3.5" />, value: `${steps_executed} steps executed`, color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
          { icon: <Network className="w-3.5 h-3.5" />, value: `${tunnels_reset} tunnels reset`, color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20' },
          { icon: <Users className="w-3.5 h-3.5" />, value: `${users_restored} users restored`, color: 'text-green-400 bg-green-500/10 border-green-500/20' },
        ].map(({ icon, value, color }) => (
          <motion.div
            key={value}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className={`flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 font-medium ${color}`}
          >
            {icon}
            {value}
          </motion.div>
        ))}
      </div>

      {/* Report text */}
      <div>
        <h3 className="text-xs font-semibold text-[#8b949e] uppercase tracking-widest mb-3">
          Root Cause &amp; Summary
        </h3>
        <div className="bg-[#161b22] rounded-lg p-4 border border-[#1c2333]">
          <p className="text-sm text-[#e6edf3] leading-relaxed whitespace-pre-wrap font-mono text-xs">
            {report.text}
          </p>
        </div>
      </div>
    </motion.div>
  )
}
