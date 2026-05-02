import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import UserChatPage from './pages/UserChatPage'
import SMEDashboardPage from './pages/SMEDashboardPage'
import AdminPage from './pages/AdminPage'
import { useAuth } from './auth'

function Require({ role, children }) {
  const me = useAuth()
  if (!me) return <Navigate to="/" replace />
  if (role && me.role !== role) {
    const dest = me.role === 'admin' ? '/admin' : me.role === 'sme' ? '/sme' : '/chat'
    return <Navigate to={dest} replace />
  }
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/chat"  element={<Require role="user"><UserChatPage /></Require>} />
      <Route path="/sme"   element={<Require role="sme"><SMEDashboardPage /></Require>} />
      <Route path="/admin" element={<Require role="admin"><AdminPage /></Require>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
