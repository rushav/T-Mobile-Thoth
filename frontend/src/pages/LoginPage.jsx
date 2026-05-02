import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listProfiles, createProfile } from '../api'
import { setUser } from '../auth'

const ROLES = [
  { key: 'user',  title: 'User',  desc: 'Ask questions, get expert answers.' },
  { key: 'sme',   title: 'SME',   desc: 'Capture and review subject knowledge.' },
  { key: 'admin', title: 'Admin', desc: 'Approve entries and triage escalations.' },
]

const ROLE_DEST = { user: '/chat', sme: '/sme', admin: '/admin' }

export default function LoginPage() {
  const navigate = useNavigate()
  const [role, setRole] = useState(null)
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newExpertise, setNewExpertise] = useState('')

  useEffect(() => { document.title = 'Thoth — Sign in' }, [])

  useEffect(() => {
    if (!role) return
    setLoading(true); setErr('')
    listProfiles(role)
      .then(setProfiles)
      .catch(e => setErr(e.message))
      .finally(() => setLoading(false))
  }, [role])

  const pick = (p) => {
    setUser(p)
    navigate(ROLE_DEST[p.role] || '/chat')
  }

  const create = async (e) => {
    e.preventDefault()
    setErr('')
    try {
      const payload = { name: newName.trim(), role }
      if (role === 'sme' && newExpertise.trim()) payload.expertise_area = newExpertise.trim()
      const p = await createProfile(payload)
      pick(p)
    } catch (e) { setErr(e.message) }
  }

  if (!role) {
    return (
      <Shell>
        <Brand />
        <p className="text-gray-500 text-sm mb-8">Select your role to continue.</p>
        <div className="w-full max-w-sm space-y-3">
          {ROLES.map(r => (
            <button
              key={r.key}
              onClick={() => setRole(r.key)}
              className="w-full bg-white border border-gray-200 rounded-2xl px-5 py-4 flex items-center text-left hover:border-[#E20074] hover:shadow-md transition-all duration-200"
            >
              <div className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0 mr-4" style={{ backgroundColor: '#E20074' }}>
                <span className="text-white font-semibold">{r.title[0]}</span>
              </div>
              <div>
                <div className="text-gray-900 font-medium">{r.title}</div>
                <div className="text-sm text-gray-500">{r.desc}</div>
              </div>
            </button>
          ))}
        </div>
      </Shell>
    )
  }

  const active = ROLES.find(r => r.key === role)

  return (
    <Shell>
      <Brand />
      <div className="w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <button onClick={() => { setRole(null); setProfiles([]); setShowCreate(false) }} className="text-sm text-gray-500 hover:text-gray-800">← Back</button>
          <span className="text-xs uppercase tracking-wide text-gray-400">{active.title}</span>
        </div>
        <h2 className="text-xl text-gray-900 mb-1">Choose your profile</h2>
        <p className="text-sm text-gray-500 mb-6">{active.desc}</p>

        {err && <div className="mb-3 rounded-md bg-rose-50 text-rose-700 text-sm px-3 py-2 border border-rose-200">{err}</div>}
        {loading ? (
          <div className="text-sm text-gray-400">Loading profiles…</div>
        ) : (
          <div className="space-y-2">
            {profiles.length === 0 && !showCreate && (
              <div className="text-sm text-gray-500 mb-2">No {active.title.toLowerCase()} profiles yet — create the first one.</div>
            )}
            {profiles.map(p => (
              <button
                key={p.id}
                onClick={() => pick(p)}
                className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center text-left hover:border-[#E20074] hover:shadow-sm transition-all"
              >
                <div className="w-9 h-9 rounded-full bg-gray-100 text-gray-700 flex items-center justify-center font-semibold mr-3">
                  {p.name.split(' ').map(s => s[0]).slice(0, 2).join('')}
                </div>
                <div className="flex-1">
                  <div className="text-gray-900">{p.name}</div>
                  {p.expertise_area && <div className="text-xs text-gray-500">{p.expertise_area}</div>}
                </div>
              </button>
            ))}
            {!showCreate && (
              <button onClick={() => setShowCreate(true)} className="w-full text-sm text-[#E20074] hover:underline mt-2">+ New {active.title.toLowerCase()} profile</button>
            )}
            {showCreate && (
              <form onSubmit={create} className="mt-3 border border-gray-200 rounded-xl p-4 space-y-3 bg-gray-50">
                <div>
                  <label className="text-xs text-gray-600">Name</label>
                  <input value={newName} onChange={e => setNewName(e.target.value)} required className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
                </div>
                {role === 'sme' && (
                  <div>
                    <label className="text-xs text-gray-600">Expertise area</label>
                    <input value={newExpertise} onChange={e => setNewExpertise(e.target.value)} placeholder="e.g. Climbing" className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
                  </div>
                )}
                <div className="flex gap-2">
                  <button type="submit" className="rounded-md text-white px-4 py-2 text-sm font-medium" style={{ backgroundColor: '#E20074' }}>Create & sign in</button>
                  <button type="button" onClick={() => setShowCreate(false)} className="rounded-md border border-gray-300 px-4 py-2 text-sm">Cancel</button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </Shell>
  )
}

function Shell({ children }) {
  return (
    <div className="h-full w-full bg-white flex flex-col items-center justify-center px-4">
      {children}
    </div>
  )
}

function Brand() {
  return (
    <>
      <h1 className="text-6xl mb-3 font-semibold tracking-tight" style={{ color: '#E20074' }}>Thoth</h1>
      <p className="text-2xl text-gray-900 mb-2">Welcome back</p>
    </>
  )
}
