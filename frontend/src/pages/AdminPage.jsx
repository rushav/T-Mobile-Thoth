import { useEffect, useState } from 'react'
import {
  currentProfile, adminPending, adminApprove, adminReject,
  adminEscalations, adminResolveEscalation, adminDirectory,
} from '../api'

export default function AdminPage() {
  const [tab, setTab] = useState('queue')
  return (
    <div className="max-w-5xl mx-auto px-6 py-4">
      <div className="flex gap-4 border-b mb-4">
        {[['queue', 'Approval Queue'], ['escalations', 'Escalations'], ['directory', 'SME Directory']].map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={[
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px',
              tab === k ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-800',
            ].join(' ')}
          >{label}</button>
        ))}
      </div>
      {tab === 'queue' && <ApprovalQueue />}
      {tab === 'escalations' && <Escalations />}
      {tab === 'directory' && <Directory />}
    </div>
  )
}

function ApprovalQueue() {
  const me = currentProfile()
  const [rows, setRows] = useState([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const refresh = async () => {
    setErr('')
    try { setRows(await adminPending()) } catch (e) { setErr(e.message) }
  }
  useEffect(() => { refresh() }, [])

  const approve = async (id) => {
    setBusy(true)
    try { await adminApprove(id, me.id); await refresh() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const reject = async (id) => {
    setBusy(true)
    try { await adminReject(id); await refresh() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3">
      {err && <div className="text-sm text-rose-600">{err}</div>}
      {rows.length === 0 && <div className="text-sm text-slate-500">Nothing pending.</div>}
      {rows.map((r) => (
        <div key={r.id} className="bg-white border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="font-semibold text-slate-800">{r.title}</div>
              <div className="text-xs text-slate-500">{r.subject_name} · by {r.contributor_name || 'unknown'}</div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => approve(r.id)} disabled={busy} className="rounded bg-emerald-600 text-white text-sm px-3 py-1 hover:bg-emerald-700">Approve</button>
              <button onClick={() => reject(r.id)} disabled={busy} className="rounded bg-rose-600 text-white text-sm px-3 py-1 hover:bg-rose-700">Reject</button>
            </div>
          </div>
          <div className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 border rounded p-3 max-h-72 overflow-auto">
            {r.content}
          </div>
        </div>
      ))}
    </div>
  )
}

function Escalations() {
  const me = currentProfile()
  const [rows, setRows] = useState([])
  const [drafts, setDrafts] = useState({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const refresh = async () => {
    setErr('')
    try { setRows(await adminEscalations()) } catch (e) { setErr(e.message) }
  }
  useEffect(() => { refresh() }, [])

  const resolve = async (id) => {
    const text = (drafts[id] || '').trim()
    if (!text) return
    setBusy(true)
    try {
      await adminResolveEscalation(id, text, me.id)
      setDrafts((d) => ({ ...d, [id]: '' }))
      await refresh()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3">
      {err && <div className="text-sm text-rose-600">{err}</div>}
      {rows.length === 0 && <div className="text-sm text-slate-500">No open escalations.</div>}
      {rows.map((r) => (
        <div key={r.id} className="bg-white border rounded-lg p-4">
          <div className="text-xs text-slate-500">From: {r.user_name || `user ${r.user_id || ''}`}</div>
          <div className="font-medium text-slate-800 mt-1">Q: {r.user_query}</div>
          {r.reason && <div className="text-xs text-slate-500 mt-1">Reason: {r.reason}</div>}
          <div className="mt-3">
            <textarea
              value={drafts[r.id] || ''}
              onChange={(e) => setDrafts((d) => ({ ...d, [r.id]: e.target.value }))}
              rows={3}
              placeholder="Your response…"
              className="w-full rounded border border-slate-300 p-2 text-sm"
            />
            <div className="mt-2 flex justify-end">
              <button
                onClick={() => resolve(r.id)}
                disabled={busy || !(drafts[r.id] || '').trim()}
                className="rounded bg-indigo-600 text-white text-sm px-3 py-1 hover:bg-indigo-700 disabled:bg-slate-300"
              >
                Resolve
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function Directory() {
  const [rows, setRows] = useState([])
  const [err, setErr] = useState('')
  useEffect(() => { adminDirectory().then(setRows).catch((e) => setErr(e.message)) }, [])
  return (
    <div className="space-y-3">
      {err && <div className="text-sm text-rose-600">{err}</div>}
      {rows.map((g, i) => (
        <div key={i} className="bg-white border rounded-lg p-4">
          <div className="font-semibold text-slate-800">{g.subject_name}</div>
          {g.description && <div className="text-xs text-slate-500 mb-2">{g.description}</div>}
          <ul className="text-sm text-slate-700 space-y-1 mt-2">
            {g.smes.map((s) => (
              <li key={s.id} className="flex items-center justify-between border-t pt-1">
                <span>{s.name}</span>
                {s.expertise_area && <span className="text-xs text-slate-500">{s.expertise_area}</span>}
              </li>
            ))}
            {g.smes.length === 0 && <li className="text-xs text-slate-400">No SMEs assigned.</li>}
          </ul>
        </div>
      ))}
    </div>
  )
}
