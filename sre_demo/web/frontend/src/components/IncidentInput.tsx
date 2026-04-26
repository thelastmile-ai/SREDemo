import { useState } from 'react'
import { motion } from 'framer-motion'
import { Send, Terminal } from 'lucide-react'
import ExampleChips from './ExampleChips'

interface IncidentInputProps {
  onSubmit: (message: string) => Promise<void>
}

export default function IncidentInput({ onSubmit }: IncidentInputProps) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)

  const canSubmit = text.trim().length >= 10 && !loading

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setLoading(true)
    try {
      await onSubmit(text.trim())
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center justify-center h-full w-full px-4"
    >
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center shadow-lg">
            <Terminal className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-white font-semibold text-lg leading-tight">
              Describe the Incident
            </h2>
            <p className="text-[#8b949e] text-xs">
              AgentCore will investigate, plan, and resolve it autonomously
            </p>
          </div>
        </div>

        {/* Example chips */}
        <div className="mb-4">
          <ExampleChips onSelect={t => setText(t)} />
        </div>

        {/* Input form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder='Describe an incident… e.g. "VPN tunnels flapping on Boston link"'
            rows={4}
            className="w-full bg-[#0d1117] border border-[#1c2333] rounded-xl px-4 py-3
                       text-sm text-[#e6edf3] placeholder-[#484f58] resize-none
                       focus:outline-none focus:border-purple-500/50 focus:ring-1
                       focus:ring-purple-500/20 transition-colors"
            onKeyDown={e => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e as unknown as React.FormEvent)
            }}
          />

          <div className="flex items-center justify-between">
            <span className={`text-xs transition-colors ${text.length >= 10 ? 'text-[#484f58]' : 'text-[#484f58]'}`}>
              {text.length < 10 && text.length > 0
                ? `${10 - text.length} more characters needed`
                : text.length >= 10
                  ? '⌘↵ to submit'
                  : ''}
            </span>

            <motion.button
              type="submit"
              disabled={!canSubmit}
              whileHover={canSubmit ? { scale: 1.02 } : {}}
              whileTap={canSubmit ? { scale: 0.98 } : {}}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium
                         transition-all duration-200
                         ${canSubmit
                           ? 'bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-500/20 cursor-pointer'
                           : 'bg-[#161b22] text-[#484f58] border border-[#1c2333] cursor-not-allowed'
                         }`}
            >
              {loading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Starting…
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  Investigate
                </>
              )}
            </motion.button>
          </div>
        </form>
      </div>
    </motion.div>
  )
}
