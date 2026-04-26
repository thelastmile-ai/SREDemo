import type { HistoryEntry } from './types'

const base = ''

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${base}${path}`)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  login: (username: string, password: string) =>
    post<{ session_id: string; username: string; model: string }>('/api/login', {
      username,
      password,
    }),

  start: (session_id: string, message: string) =>
    post<{ started: boolean }>('/api/start', { session_id, message }),

  approve: (session_id: string, response = 'approved') =>
    post<{ resumed: boolean }>('/api/approve', { session_id, response }),

  clarify: (session_id: string, answer: string) =>
    post<{ clarified: boolean }>('/api/clarify', { session_id, answer }),

  history: () =>
    get<HistoryEntry[]>('/api/history'),
}
