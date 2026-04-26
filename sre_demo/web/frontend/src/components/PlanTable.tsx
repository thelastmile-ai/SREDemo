import { motion } from 'framer-motion'
import { GitBranch } from 'lucide-react'
import type { PlanStep } from '../lib/types'

interface Props {
  steps: PlanStep[]
}

const TOOL_PROVIDER: Record<string, { label: string; color: string }> = {
  aws: { label: 'AWS', color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' },
  dd: { label: 'Datadog', color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
  pd: { label: 'PagerDuty', color: 'text-green-400 bg-green-500/10 border-green-500/20' },
  network: { label: 'Network', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20' },
}

function toolProvider(toolName: string) {
  const prefix = toolName.split('_')[0]
  return TOOL_PROVIDER[prefix] ?? { label: 'Tool', color: 'text-[#8b949e] bg-[#161b22] border-[#1c2333]' }
}

export default function PlanTable({ steps }: Props) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <GitBranch className="w-4 h-4 text-purple-400" />
        <h3 className="text-sm font-semibold text-white">Remediation Plan</h3>
        <span className="text-xs text-purple-300 bg-purple-500/10 border border-purple-500/20 rounded px-2 py-0.5">
          {steps.length} steps
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#1c2333]">
              <th className="text-left text-[#8b949e] font-medium py-2 pr-4 w-10">#</th>
              <th className="text-left text-[#8b949e] font-medium py-2 pr-4">Tool</th>
              <th className="text-left text-[#8b949e] font-medium py-2 pr-4">Provider</th>
              <th className="text-left text-[#8b949e] font-medium py-2 pr-4">Dependencies</th>
              <th className="text-left text-[#8b949e] font-medium py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step, i) => {
              const provider = toolProvider(step.tool)
              return (
                <motion.tr
                  key={step.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="border-b border-[#1c2333]/50 hover:bg-[#161b22] transition-colors"
                >
                  <td className="py-2.5 pr-4 text-[#484f58] font-mono">{i + 1}</td>
                  <td className="py-2.5 pr-4 text-white font-mono">{step.tool}</td>
                  <td className="py-2.5 pr-4">
                    <span className={`text-[10px] border rounded px-1.5 py-0.5 ${provider.color}`}>
                      {provider.label}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 text-[#8b949e] font-mono">
                    {step.dependencies.length > 0 ? step.dependencies.join(', ') : '—'}
                  </td>
                  <td className="py-2.5">
                    <span className="text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded px-1.5 py-0.5 uppercase">
                      {step.status || 'PENDING'}
                    </span>
                  </td>
                </motion.tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
