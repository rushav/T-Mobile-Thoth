import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listProfiles, listSubjects, createProfile, setProfile } from '../api'

const ROLE_PATHS = { user: '/chat', sme: '/sme', admin: '/admin' }

export default function LoginPage() {
  const [role, setRole] = useState(null)
  const [profiles, setProfiles] = useState([])
  const [subjects, setSubjects] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newExpertise, setNewExpertise] = useState('')
  const [newSubjectIds, setNewSubjectIds] = useState([])
  const [err, setErr] = useState('')
  const nav = useNavigate()

  useEffect(() => { listSubjects().then(setSubjects).catch(() => {}) }, [])

  useEffect(() => {
    if (!role) return
    setErr('')
    listProfiles(role).then(setProfiles).catch((e) => setErr(e.message))
  }, [role])

  const pick = (p) => {
    setProfile(p)
    nav(ROLE_PATHS[p.role])
  }

  const create = async (e) => {
    e.preventDefault()
    try {
      const payload = { name: newName, role, expertise_area: newExpertise || null }
      if (role === 'sme') payload.subject_ids = newSubjectIds
      const p = await createProfile(payload)
      setProfile(p)
      nav(ROLE_PATHS[role])
    } catch (e) { setErr(e.message) }
  }

  return (
    <div className="min-h-full flex items-center justify-center p-8">
      <div className="w-full max-w-xl bg-white border rounded-xl shadow-sm p-8">
        <h1 className="text-2xl font-bold text-slate-800">Project Thoth</h1>
        <p className="text-sm text-slate-500 mb-6">AI-powered SME knowledge capture & retrieval</p>

        {!role && (
          <div>
            <div className="text-sm font-medium text-slate-700 mb-2">Select your role</div>
            <div className="grid grid-cols-3 gap-3">
              {['user', 'sme', 'admin'].map((r) => (
                <button
                  key={r}
                  onClick={() => setRole(r)}
                  className="rounded-lg border border-slate-300 p-4 hover:border-indigo-500 hover:bg-indigo-50 text-center"
                >
                  <div className="text-base font-semibold capitalize text-slate-800">{r}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {r === 'user' && 'Ask questions'}
                    {r === 'sme' && 'Contribute knowledge'}
                    {r === 'admin' && 'Approve & manage'}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {role && !showCreate && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <button onClick={() => setRole(null)} className="text-sm text-slate-500 hover:text-slate-700">← Back</button>
              <div className="text-sm font-medium text-slate-700 capitalize">Choose a {role} profile</div>
              <button onClick={() => setShowCreate(true)} className="text-sm text-indigo-600 hover:text-indigo-800">+ New</button>
            </div>
            {err && <div className="text-sm text-rose-600 mb-2">{err}</div>}
            <div className="space-y-2">
              {profiles.map((p) => (
                <button
                  key={p.id}
                  onClick={() => pick(p)}
                  className="w-full text-left rounded-lg border border-slate-200 p-3 hover:border-indigo-500 hover:bg-indigo-50"
                >
                  <div className="font-medium text-slate-800">{p.name}</div>
                  {p.expertise_area && <div className="text-xs text-slate-500">{p.expertise_area}</div>}
                </button>
              ))}
              {profiles.length === 0 && <div className="text-sm text-slate-400">No profiles yet.</div>}
            </div>
          </div>
        )}

        {role && showCreate && (
          <form onSubmit={create} className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <button type="button" onClick={() => setShowCreate(false)} className="text-sm text-slate-500 hover:text-slate-700">← Back</button>
              <div className="text-sm font-medium text-slate-700 capitalize">New {role} profile</div>
              <span />
            </div>
            <div>
              <label className="text-sm text-slate-700">Name</label>
              <input value={newName} onChange={(e) => setNewName(e.target.value)} required className="mt-1 w-full rounded border border-slate-300 p-2 text-sm" />
            </div>
            {role === 'sme' && (
              <>
                <div>
                  <label className="text-sm text-slate-700">Expertise area</label>
                  <input value={newExpertise} onChange={(e) => setNewExpertise(e.target.value)} className="mt-1 w-full rounded border border-slate-300 p-2 text-sm" />
                </div>
                <div>
                  <label className="text-sm text-slate-700">Subjects</label>
                  <div className="mt-1 grid grid-cols-2 gap-2">
                    {subjects.map((s) => (
                      <label key={s.id} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={newSubjectIds.includes(s.id)}
                          onChange={(e) => setNewSubjectIds((ids) => e.target.checked ? [...ids, s.id] : ids.filter((x) => x !== s.id))}
                        />
                        {s.name}
                      </label>
                    ))}
                  </div>
                </div>
              </>
            )}
            {err && <div className="text-sm text-rose-600">{err}</div>}
            <button type="submit" className="rounded bg-indigo-600 text-white px-4 py-2 text-sm font-medium hover:bg-indigo-700">Create & log in</button>
          </form>
        )}
      </div>
    </div>
  )
}
