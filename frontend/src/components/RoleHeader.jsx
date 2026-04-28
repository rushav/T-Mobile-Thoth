import { useEffect, useState } from 'react'
import { listProfiles, createProfile, currentProfile, setProfile, getProfile } from '../api'

const ROLE_THEMES = {
  user:    { bar: 'bg-blue-700',   accent: 'text-blue-100',   label: 'User View' },
  sme:     { bar: 'bg-teal-700',   accent: 'text-teal-100',   label: 'SME View' },
  admin:   { bar: 'bg-rose-700',   accent: 'text-rose-100',   label: 'Admin View' },
  support: { bar: 'bg-slate-700',  accent: 'text-slate-200',  label: 'Support View' },
}

/**
 * Header bar with a built-in profile selector for the current role.
 *
 * The selected profile is stored per-role in localStorage (see api.js currentProfile).
 * Calls onProfileChange when the user picks or creates a profile so the page can refresh.
 */
export default function RoleHeader({ role, onProfileChange }) {
  const theme = ROLE_THEMES[role] || ROLE_THEMES.user
  const [profiles, setProfiles] = useState([])
  const [active, setActive] = useState(currentProfile(role))
  const [creating, setCreating] = useState(false)
  const [err, setErr] = useState('')

  // New profile form state
  const [newName, setNewName] = useState('')
  const [newContact, setNewContact] = useState('')
  const [newExpertise, setNewExpertise] = useState('')

  const refreshList = async () => {
    try {
      const list = await listProfiles(role)
      setProfiles(list)
      // If the currently-selected profile was deleted, clear it.
      if (active && !list.find((p) => p.id === active.id)) {
        setProfile(role, null)
        setActive(null)
        onProfileChange?.(null)
      }
    } catch (e) { setErr(e.message) }
  }

  useEffect(() => { refreshList() }, [role])

  // If a profile is selected, refresh it from the backend so review-request
  // flags etc. are current when this window comes back into focus.
  useEffect(() => {
    if (!active) return
    let cancelled = false
    getProfile(active.id).then((p) => {
      if (cancelled) return
      setActive(p)
      setProfile(role, p)
    }).catch(() => {})
    return () => { cancelled = true }
  }, [])

  const select = (id) => {
    if (id === '__new__') { setCreating(true); return }
    if (!id) {
      setProfile(role, null)
      setActive(null)
      onProfileChange?.(null)
      return
    }
    const p = profiles.find((x) => String(x.id) === String(id))
    if (!p) return
    setProfile(role, p)
    setActive(p)
    onProfileChange?.(p)
  }

  const submitNew = async (e) => {
    e.preventDefault()
    if (!newName.trim()) return
    setErr('')
    try {
      const payload = {
        name: newName.trim(),
        role,
        contact_info: newContact.trim() || null,
        expertise_area: role === 'sme' ? (newExpertise.trim() || null) : null,
      }
      const p = await createProfile(payload)
      setProfile(role, p)
      setActive(p)
      onProfileChange?.(p)
      setCreating(false)
      setNewName(''); setNewContact(''); setNewExpertise('')
      await refreshList()
    } catch (e) { setErr(e.message) }
  }

  return (
    <header className={`${theme.bar} text-white px-6 py-3 shadow-md`}>
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="text-xl font-semibold tracking-tight">Project Thoth</div>
          <span className={`text-sm uppercase tracking-wider px-2 py-0.5 rounded bg-white/15 ${theme.accent}`}>
            {theme.label}
          </span>
          <div className="text-sm opacity-90 truncate">
            — {active ? active.name : 'no profile selected'}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!creating && (
            <select
              value={active ? String(active.id) : ''}
              onChange={(e) => select(e.target.value)}
              className="rounded bg-white/95 text-slate-800 text-sm px-2 py-1"
            >
              <option value="">— pick a {role} —</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
              <option value="__new__">+ Create new {role}…</option>
            </select>
          )}
          {creating && (
            <button
              onClick={() => { setCreating(false); setErr('') }}
              className="text-xs rounded border border-white/40 px-2 py-1 hover:bg-white/10"
            >Cancel</button>
          )}
        </div>
      </div>

      {creating && (
        <form onSubmit={submitNew} className="mt-3 grid grid-cols-1 md:grid-cols-4 gap-2 items-end bg-white/10 rounded p-3">
          <label className="text-sm">
            <div className="text-xs opacity-80 mb-0.5">Name</div>
            <input value={newName} onChange={(e) => setNewName(e.target.value)} required
              className="w-full rounded bg-white text-slate-800 text-sm px-2 py-1" />
          </label>
          <label className="text-sm">
            <div className="text-xs opacity-80 mb-0.5">Contact info</div>
            <input value={newContact} onChange={(e) => setNewContact(e.target.value)}
              placeholder="email / Slack / phone"
              className="w-full rounded bg-white text-slate-800 text-sm px-2 py-1" />
          </label>
          {role === 'sme' && (
            <label className="text-sm">
              <div className="text-xs opacity-80 mb-0.5">Expertise area</div>
              <input value={newExpertise} onChange={(e) => setNewExpertise(e.target.value)}
                placeholder="e.g. Brewing Methods"
                className="w-full rounded bg-white text-slate-800 text-sm px-2 py-1" />
            </label>
          )}
          <button type="submit" className="rounded bg-white text-slate-800 text-sm font-medium px-3 py-1 hover:bg-white/90">
            Create
          </button>
          {err && <div className="md:col-span-4 text-xs bg-rose-600/30 rounded px-2 py-1">{err}</div>}
        </form>
      )}
    </header>
  )
}
