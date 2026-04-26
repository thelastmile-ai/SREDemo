import { Routes, Route, Navigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'

function RequireSession({ children }: { children: React.ReactNode }) {
  const hasSession = !!sessionStorage.getItem('sre_demo_session')
  return hasSession ? <>{children}</> : <Navigate to="/" replace />
}

export default function App() {
  return (
    <AnimatePresence mode="wait">
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route
          path="/demo"
          element={
            <RequireSession>
              <DashboardPage />
            </RequireSession>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  )
}
