import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, Circle, Loader2, AlertCircle, Bot, Search, GitBranch, UserCheck, Cpu, FileText } from 'lucide-react'
import type { NodeEntry } from '../lib/types'

const NODE_ICONS: Record<string, React.ReactNode> = {
  extract_intent: <Search className="w-4 h-4" />,
  extract_entities: <Bot className="w-4 h-4" />,
  plan: <GitBranch className="w-4 h-4" />,
  hitl_review: <UserCheck className="w-4 h-4" />,
  validate_cot: <Cpu className="w-4 h-4" />,
  execute_step: <Cpu className="w-4 h-4" />,
  report: <FileText className="w-4 h-4" />,
}

const NODE_LABELS: Record<string, string> = {
  extract_intent: 'Intent Classification',
  extract_entities: 'Entity Extraction',
  plan: 'Remediation Planning',
  hitl_review: 'Human Approval Gate',
  validate_cot: 'Chain-of-Thought Validation',
  execute_step: 'Tool Execution',
  report: 'Incident Report',
}

interface Props {
  nodes: NodeEntry[]
}

export default function ActivityFeed({ nodes }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [nodes.length])

  return (
    <div className="bg-[#0d1117] border border-[#1c2333] rounded-xl p-5 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4 flex-shrink-0">
        <div className="w-2 h-2 rounded-full bg-purple-400" />
        <h3 className="text-xs font-semibold text-[#8b949e] uppercase tracking-widest">
          Agent Activity
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1 min-h-0 pr-1">
        <AnimatePresence initial={false}>
          {nodes.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-32 text-[#484f58] text-xs"
            >
              <Circle className="w-8 h-8 mb-2 opacity-30" />
              Waiting for agent to start…
            </motion.div>
          )}
          {nodes.map((entry, idx) => (
            <motion.div
              key={`${entry.node}-${idx}`}
              initial={{ opacity: 0, x: -16, height: 0 }}
              animate={{ opacity: 1, x: 0, height: 'auto' }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="flex items-start gap-3 py-2.5 px-3 rounded-lg hover:bg-[#161b22] transition-colors"
            >
              {/* Status icon */}
              <div className="flex-shrink-0 mt-0.5">
                {entry.status === 'running' ? (
                  <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />
                ) : entry.status === 'done' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-400" />
                ) : entry.status === 'error' ? (
                  <AlertCircle className="w-4 h-4 text-red-400" />
                ) : (
                  <Circle className="w-4 h-4 text-[#484f58]" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[#8b949e]">
                    {NODE_ICONS[entry.node] ?? <Circle className="w-4 h-4" />}
                  </span>
                  <span
                    className={`text-sm font-medium ${
                      entry.status === 'running'
                        ? 'text-purple-300'
                        : entry.status === 'done'
                          ? 'text-white'
                          : 'text-[#8b949e]'
                    }`}
                  >
                    {NODE_LABELS[entry.node] ?? entry.node}
                  </span>
                  {entry.status === 'running' && (
                    <span className="text-[10px] text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded border border-purple-500/20 animate-pulse">
                      running
                    </span>
                  )}
                  {entry.status === 'done' && (
                    <span className="text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">
                      ✓ complete
                    </span>
                  )}
                </div>
                {entry.finishedAt && entry.startedAt && (
                  <p className="text-[10px] text-[#484f58] mt-0.5 font-mono">
                    {((entry.finishedAt - entry.startedAt) / 1000).toFixed(1)}s
                  </p>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
