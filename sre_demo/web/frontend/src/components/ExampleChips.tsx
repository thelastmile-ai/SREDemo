import { Zap } from 'lucide-react'

const EXAMPLES = [
  {
    label: '🔌 VPN Flap',
    text: 'VPN tunnels are flapping between Boston and Chicago — BGP sessions dropping intermittently',
  },
  {
    label: '🐘 DB Overload',
    text: "PostgreSQL connection pool exhausted on checkout-service — getting 'too many connections' errors",
  },
  {
    label: '☸ K8s Crashloop',
    text: 'payment-service pods are crashlooping in production — OOMKilled, restarting every 30 seconds',
  },
  {
    label: '🔒 SSL Expiry',
    text: 'SSL certificate expired on api.acme.com — users getting browser security warnings',
  },
]

interface ExampleChipsProps {
  onSelect: (text: string) => void
}

export default function ExampleChips({ onSelect }: ExampleChipsProps) {
  return (
    <div className="w-full">
      <p className="text-[10px] text-[#484f58] uppercase tracking-widest mb-2 flex items-center gap-1">
        <Zap className="w-3 h-3" />
        Try an example
      </p>
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map(ex => (
          <button
            key={ex.label}
            type="button"
            onClick={() => onSelect(ex.text)}
            className="text-xs text-[#8b949e] bg-[#161b22] border border-[#1c2333]
                       rounded-full px-3 py-1 hover:border-purple-500/50 hover:text-white
                       hover:bg-purple-500/10 transition-all duration-150 cursor-pointer"
          >
            {ex.label}
          </button>
        ))}
      </div>
    </div>
  )
}
