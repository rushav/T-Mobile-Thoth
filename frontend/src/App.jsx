import { Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import UserChatPage from './pages/UserChatPage'
import SMEDashboardPage from './pages/SMEDashboardPage'
import AdminPage from './pages/AdminPage'
import SupportPage from './pages/SupportPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/user" element={<UserChatPage />} />
      <Route path="/sme" element={<SMEDashboardPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route path="/support" element={<SupportPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
