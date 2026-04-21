import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { currentProfile, setProfile } from './api'
import LoginPage from './pages/LoginPage'
import UserChatPage from './pages/UserChatPage'
import SMEDashboardPage from './pages/SMEDashboardPage'
import AdminPage from './pages/AdminPage'

function Header() {
  const p = currentProfile()
  const nav = useNavigate()
  if (!p) return null
  const logout = () => {
    setProfile(null)
    nav('/')
  }
  return (
    <header className="flex items-center justify-between bg-white border-b px-6 py-3 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="text-xl font-semibold text-slate-800">Project Thoth</div>
        <span className="text-xs uppercase tracking-wider px-2 py-1 rounded bg-slate-200 text-slate-700">{p.role}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-700">{p.name}</span>
        <button onClick={logout} className="text-sm px-3 py-1 rounded border border-slate-300 hover:bg-slate-100">Log out</button>
      </div>
    </header>
  )
}

function Protected({ role, children }) {
  const p = currentProfile()
  if (!p) return <Navigate to="/" replace />
  if (role && p.role !== role) return <Navigate to="/" replace />
  return (
    <div className="flex flex-col h-full">
      <Header />
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/chat" element={<Protected role="user"><UserChatPage /></Protected>} />
      <Route path="/sme" element={<Protected role="sme"><SMEDashboardPage /></Protected>} />
      <Route path="/admin" element={<Protected role="admin"><AdminPage /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
