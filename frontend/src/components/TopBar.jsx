import { useNavigate } from 'react-router-dom'
import { useAuth, clearUser } from '../auth'

const ROLE_LABEL = { user: 'User', sme: 'SME', admin: 'Admin' }

export default function TopBar() {
  const navigate = useNavigate()
  const me = useAuth()
  if (!me) return null

  const initials = me.name.split(' ').map(s => s[0]).slice(0, 2).join('')

  const logout = () => {
    clearUser()
    navigate('/')
  }

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="font-semibold text-xl tracking-tight" style={{ color: '#E20074' }}>Thoth</div>
          <span className="text-xs uppercase tracking-wide text-gray-400">{ROLE_LABEL[me.role] || me.role}</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 text-sm text-gray-700">
            <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-xs font-semibold">{initials}</div>
            <div>
              <div className="leading-tight">{me.name}</div>
              {me.expertise_area && <div className="text-xs text-gray-400 leading-tight">{me.expertise_area}</div>}
            </div>
          </div>
          <button
            onClick={logout}
            className="text-sm rounded-md border border-gray-300 px-3 py-1.5 text-gray-700 hover:border-[#E20074] hover:text-[#E20074]"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  )
}
