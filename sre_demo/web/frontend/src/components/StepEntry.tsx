import { useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react'
import type { StepResult } from '../lib/types'

const TOOL_PROVIDER: Record<string, { label: string; color: string }> = {
  aws: { label: 'AWS', color: 'text-orange-400' },
  dd: { label: 'Datadog', color: 'text-purple-400' },
  pd: { label: 'PagerDuty', color: 'text-green-400' },
  network: { label: 'Network', color: 'text-cyan-400' },
}

function getProvider(toolName: string) {
  const prefix = toolName.split('_')[0]
  return TOOL_PROVIDER[prefix] ?? { label: 'Tool', color: 'text-[#8b949e]' }
}

interface Props {
  step: StepResult
  index: number
}

export default function StepEntry({ step, index }: Props) {
  const [expanded, setExpanded] = useState(false)
  const isRunning = step.status === 'RUNNING' || step.status === 'running'
  const isFailed = step.status === 'FAILED' || step.status === 'failed' || step.status === 'error'
  const provider = getProvider(step.tool || step.step_id)

  const outputStr = step.output != null ? JSON.stringify(step.output, null, 2) : ''
  const preview = outputStr.slice(0, 120) + (outputStr.length > 120 ? '…' : '')

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className="bg-[#161b22] border border-[#1c2333] rounded-lg p-3.5 hover:border-[#30363d] transition-colors"
    >
      <div className="flex items-start gap-3">
        {/* Status icon */}
        <div className="flex-shrink-0 mt-0.5">
          {isRunning ? (
            <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />
          ) : isFailed ? (
            <XCircle className="w-4 h-4 text-red-400" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-green-400" />
          )}
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs font-medium ${provider.color}`}>
              {provider.label}
            </span>
            <span className="text-sm text-white font-mono truncate">
              {step.tool || step.step_id}
            </span>
            <span
              className={`text-[10px] rounded px-1.5 py-0.5 border uppercase ${
                isRunning
                  ? 'text-purple-400 bg-purple-500/10 border-purple-500/20'
                  : isFailed
                    ? 'text-red-400 bg-red-500/10 border-red-500/20'
                    : 'text-green-400 bg-green-500/10 border-green-500/20'
              }`}
            >
              {isRunning ? 'running' : isFailed ? 'failed' : 'completed'}
            </span>
            {step.timestamp && (
              <span className="text-[10px] text-[#484f58] font-mono ml-auto">
                {new Date(step.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>

          {/* Output preview */}
          {outputStr && (
            <div className="mt-2">
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-[#8b949e] text-xs hover:text-white transition-colors"
              >
                {expanded ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
                {expanded ? 'Hide output' : 'Show output'}
              </button>

              {!expanded && (
                <p className="text-[11px] text-[#8b949e] font-mono mt-1 truncate">
                  {preview}
                </p>
              )}

              {expanded && (
                <motion.pre
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  className="text-[11px] text-[#8b949e] font-mono mt-2 bg-[#0d1117] border border-[#1c2333] rounded p-3 overflow-x-auto max-h-48 overflow-y-auto"
                >
                  {outputStr}
                </motion.pre>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
