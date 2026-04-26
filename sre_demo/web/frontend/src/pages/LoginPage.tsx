import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, Terminal, Zap, Shield, Activity } from 'lucide-react'
import { api } from '../lib/api'
import { useSession } from '../hooks/useSession'

export default function LoginPage() {
  const navigate = useNavigate()
  const { saveSession } = useSession()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [shake, setShake] = useState(false)
  const formRef = useRef<HTMLFormElement>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const session = await api.login(username || 'demo', password || 'demo')
      saveSession(session)
      navigate('/demo')
    } catch (err: unknown) {
      setLoading(false)
      setError(err instanceof Error ? err.message : 'Login failed')
      setShake(true)
      setTimeout(() => setShake(false), 600)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#080b10] relative overflow-hidden">
      {/* Animated background grid */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(168,85,247,1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(168,85,247,1) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
        }}
      />

      {/* Radial gradient glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(168,85,247,0.15),transparent)]" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -24 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-md px-6"
      >
        {/* Logo / brand */}
        <div className="text-center mb-10">
          <motion.div
            animate={{ opacity: [0.7, 1, 0.7] }}
            transition={{ repeat: Infinity, duration: 3, ease: 'easeInOut' }}
            className="inline-flex items-center gap-2 mb-4"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-900/50">
              <Terminal className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-bold text-white tracking-tight">
              AgentCore
              <span className="text-purple-400 ml-1">·</span>
              <span className="text-[#8b949e] font-normal ml-1 text-lg">SRE Demo</span>
            </span>
          </motion.div>
          <p className="text-[#8b949e] text-sm leading-relaxed">
            AI-powered incident remediation —{' '}
            <span className="text-purple-400">Claude + LangGraph</span>
          </p>
        </div>

        {/* Login card */}
        <motion.div
          animate={shake ? { x: [-8, 8, -6, 6, -4, 4, 0] } : { x: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="bg-[#0d1117] border border-[#1c2333] rounded-2xl p-8 shadow-2xl shadow-black/60">
            <form ref={formRef} onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-[#8b949e] uppercase tracking-widest mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="sre-operator"
                  autoComplete="username"
                  className={`w-full px-4 py-3 bg-[#161b22] border rounded-lg text-white text-sm placeholder-[#484f58] outline-none transition-all duration-200
                    focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50
                    ${error ? 'border-red-500/60' : 'border-[#30363d]'}`}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#8b949e] uppercase tracking-widest mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className={`w-full px-4 py-3 bg-[#161b22] border rounded-lg text-white text-sm placeholder-[#484f58] outline-none transition-all duration-200
                    focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50
                    ${error ? 'border-red-500/60' : 'border-[#30363d]'}`}
                />
              </div>

              <AnimatePresence>
                {error && (
                  <motion.p
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2"
                  >
                    {error}
                  </motion.p>
                )}
              </AnimatePresence>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-lg font-semibold text-sm text-white transition-all duration-200
                  bg-gradient-to-r from-purple-600 to-indigo-600
                  hover:from-purple-500 hover:to-indigo-500
                  hover:shadow-lg hover:shadow-purple-900/40 hover:scale-[1.02]
                  active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:scale-100
                  flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Starting session…
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Start Demo
                  </>
                )}
              </button>
            </form>

            <p className="text-center text-[#484f58] text-xs mt-5">
              Synthetic mode — any credentials accepted
            </p>
          </div>
        </motion.div>

        {/* Platform badge row */}
        <div className="flex items-center justify-center gap-6 mt-8">
          {[
            { icon: <Shield className="w-4 h-4" />, label: 'Anthropic Claude' },
            { icon: <Activity className="w-4 h-4" />, label: 'LangGraph' },
            { icon: <Terminal className="w-4 h-4" />, label: 'AgentCore' },
          ].map(({ icon, label }) => (
            <div key={label} className="flex items-center gap-1.5 text-[#484f58] text-xs">
              {icon}
              <span>{label}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
