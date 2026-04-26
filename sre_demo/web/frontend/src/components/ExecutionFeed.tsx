import { motion } from 'framer-motion'
import { Cpu } from 'lucide-react'
import StepEntry from './StepEntry'
import type { StepResult } from '../lib/types'

interface Props {
  steps: StepResult[]
}

export default function ExecutionFeed({ steps }: Props) {
  if (steps.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[#0d1117] border border-[#1c2333] rounded-xl p-5"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="w-7 h-7 rounded-lg bg-purple-500/15 flex items-center justify-center">
          <Cpu className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <h3 className="text-xs font-semibold text-[#8b949e] uppercase tracking-widest">
          Execution Feed
        </h3>
        <span className="text-xs text-purple-300 bg-purple-500/10 border border-purple-500/20 rounded px-2 py-0.5 ml-auto">
          {steps.length} steps
        </span>
      </div>
      <div className="space-y-2">
        {steps.map((step, i) => (
          <StepEntry key={step.step_id} step={step} index={i} />
        ))}
      </div>
    </motion.div>
  )
}
