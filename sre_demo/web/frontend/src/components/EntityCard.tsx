import { motion } from 'framer-motion'
import { Database } from 'lucide-react'
import type { EntityMap } from '../lib/types'

interface Props {
  entities: EntityMap | null
}

const FIELD_LABELS: Record<string, string> = {
  incident_type: 'Type',
  severity: 'Severity',
  ike_phase: 'IKE Phase',
  ike_failure_reason: 'Failure Reason',
  affected_branches: 'Branches',
  affected_services: 'Services',
  customer_facing: 'Customer-Facing',
  vpn_gateway: 'VPN Gateway',
  vpn_connection_ids: 'Connection IDs',
  customer_gateway_id: 'Customer GW',
}

export default function EntityCard({ entities }: Props) {
  if (!entities) return null

  const allFields: [string, unknown][] = []
  for (const [, entity] of Object.entries(entities)) {
    for (const [k, v] of Object.entries(entity as Record<string, unknown>)) {
      if (v !== null && v !== undefined) allFields.push([k, v])
    }
  }

  if (allFields.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-[#0d1117] border border-[#1c2333] rounded-xl p-5 mt-3"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="w-7 h-7 rounded-lg bg-indigo-500/15 flex items-center justify-center">
          <Database className="w-3.5 h-3.5 text-indigo-400" />
        </div>
        <h3 className="text-xs font-semibold text-[#8b949e] uppercase tracking-widest">
          Extracted Entities
        </h3>
      </div>

      <div className="grid grid-cols-1 gap-y-2">
        {allFields.map(([key, value]) => (
          <motion.div
            key={key}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="flex items-start gap-3"
          >
            <span className="text-[10px] text-[#8b949e] uppercase tracking-wide w-28 flex-shrink-0 pt-0.5">
              {FIELD_LABELS[key] ?? key}
            </span>
            <span className="text-xs text-[#e6edf3] font-mono break-all">
              {Array.isArray(value)
                ? value.join(', ')
                : typeof value === 'boolean'
                  ? value ? 'Yes' : 'No'
                  : String(value)}
            </span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
