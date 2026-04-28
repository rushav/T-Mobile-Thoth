import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import RoleHeader from '../components/RoleHeader'
import {
  currentProfile, adminPending, adminApprove, adminReject,
  adminEscalations, adminResolveEscalation,
  adminDirectory, adminRequestReview,
} from '../api'

const POLL_MS = 5000

export default function AdminPage() {
  const [me, setMe] = useState(currentProfile('admin'))
  const [tab, setTab] = useState('queue')

  return (
    <div className="flex flex-col h-full">
      <RoleHeader role="admin" onProfileChange={setMe} />
      {!me ? (
        <div className="flex-1 flex items-center justify-center text-sm text-slate-500">
          Pick or create an admin profile in the header to start.
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <div className="max-w-5xl mx-auto px-6 py-4">
            <div className="flex gap-4 border-b mb-4">
              {[['queue', 'Approval Queue'], ['escalations', 'Escalations'], ['directory', 'SME Directory']].map(([k, label]) => (
                <button
                  key={k}
                  onClick={() => setTab(k)}
                  className={[
                    'px-4 py-2 text-sm font-medium border-b-2 -mb-px',
                    tab === k ? 'border-rose-600 text-rose-700' : 'border-transparent text-slate-500 hover:text-slate-800',
                  ].join(' ')}
                >{label}</button>
              ))}
            </div>
            {tab === 'queue' && <ApprovalQueue me={me} />}
            {tab === 'escalations' && <Escalations me={me} />}
            {tab === 'directory' && <Directory me={me} />}
          </div>
        </div>
      )}
    </div>
  )
}

function ApprovalQueue({ me }) {
  const [rows, setRows] = useState([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const refresh = async () => {
    setErr('')
    try { setRows(await adminPending()) } catch (e) { setErr(e.message) }
  }
  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [])

  const approve = async (id) => {
    setBusy(true)
    try { await adminApprove(id, me.id); await refresh() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const reject = async (id) => {
    const reason = window.prompt('Reason for rejection (will be shared with the SME):') || ''
    if (!reason.trim()) return
    setBusy(true)
    try { await adminReject(id, reason); await refresh() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3">
      {err && <div className="text-sm text-rose-600">{err}</div>}
      {rows.length === 0 && <div className="text-sm text-slate-500">Nothing pending admin review.</div>}
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
          <div className="text-sm text-slate-700 bg-slate-50 border rounded p-3 max-h-72 overflow-auto">
            <ReactMarkdown>{r.content || ''}</ReactMarkdown>
          </div>
        </div>
      ))}
    </div>
  )
}

function Escalations({ me }) {
  const [view, setView] = useState('open')
  const [rows, setRows] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [resolutions, setResolutions] = useState({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const refresh = async () => {
    setErr('')
    try {
      setRows(await adminEscalations(view))
    } catch (e) { setErr(e.message) }
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [view])

  const selected = useMemo(() => rows.find((r) => r.id === selectedId) || null, [rows, selectedId])

  const resolve = async (id) => {
    const text = (resolutions[id] || '').trim()
    if (!text) return
    setBusy(true)
    try {
      await adminResolveEscalation(id, text, me.id)
      setResolutions((d) => ({ ...d, [id]: '' }))
      setSelectedId(null)
      await refresh()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <button
          onClick={() => { setView('open'); setSelectedId(null) }}
          className={['px-3 py-1 rounded border', view === 'open' ? 'border-rose-500 bg-rose-50 text-rose-700' : 'border-slate-300 text-slate-600'].join(' ')}
        >Active</button>
        <button
          onClick={() => { setView('resolved'); setSelectedId(null) }}
          className={['px-3 py-1 rounded border', view === 'resolved' ? 'border-rose-500 bg-rose-50 text-rose-700' : 'border-slate-300 text-slate-600'].join(' ')}
        >Archive</button>
      </div>
      {err && <div className="text-sm text-rose-600">{err}</div>}
      {rows.length === 0 && (
        <div className="text-sm text-slate-500">
          {view === 'open' ? 'No open escalations.' : 'Archive is empty.'}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ul className="space-y-2">
          {rows.map((r) => (
            <li key={r.id}>
              <button
                onClick={() => setSelectedId(r.id)}
                className={[
                  'w-full text-left rounded-lg border p-3 hover:bg-slate-50',
                  selectedId === r.id ? 'border-rose-500 bg-rose-50' : 'border-slate-200 bg-white'
                ].join(' ')}
              >
                <div className="text-xs text-slate-500">From {r.user_name || `user ${r.user_id || ''}`} · {r.created_at ? new Date(r.created_at).toLocaleString() : ''}</div>
                <div className="text-sm text-slate-800 mt-0.5 line-clamp-2">{r.user_query}</div>
                <div className="text-xs text-slate-500 mt-1">{r.reason}</div>
              </button>
            </li>
          ))}
        </ul>

        <div>
          {selected ? (
            <div className="bg-white border rounded-lg p-4 space-y-3 sticky top-2">
              <div>
                <div className="text-xs text-slate-500">Question</div>
                <div className="text-sm font-medium text-slate-800">{selected.user_query}</div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-xs text-slate-500">Asked by</div>
                  <div className="text-slate-800">{selected.user_name || `user ${selected.user_id || '—'}`}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Timestamp</div>
                  <div className="text-slate-800">{selected.created_at ? new Date(selected.created_at).toLocaleString() : '—'}</div>
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Reason for escalation</div>
                <div className="text-sm text-slate-800">{selected.reason || '—'}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">Subjects Thoth considered</div>
                {selected.candidates && selected.candidates.length > 0 ? (
                  <ul className="text-sm space-y-0.5">
                    {selected.candidates.map((c, i) => (
                      <li key={i} className="flex justify-between border-b last:border-b-0 py-0.5">
                        <span className="text-slate-700">{c.subject}</span>
                        <span className="text-xs text-slate-500">conf {(c.confidence ?? 0).toFixed(2)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-sm text-slate-500">No subjects scored above threshold.</div>
                )}
              </div>

              {selected.status === 'resolved' ? (
                <div>
                  <div className="text-xs text-slate-500">Resolution</div>
                  <div className="text-sm text-slate-800 whitespace-pre-wrap bg-slate-50 border rounded p-2">{selected.resolution}</div>
                  {selected.resolved_at && (
                    <div className="text-xs text-slate-500 mt-1">Resolved {new Date(selected.resolved_at).toLocaleString()}{selected.assigned_to_name ? ` by ${selected.assigned_to_name}` : ''}</div>
                  )}
                </div>
              ) : (
                <>
                  <div>
                    <label className="text-xs text-slate-500">Resolution</label>
                    <textarea
                      rows={4}
                      value={resolutions[selected.id] || ''}
                      onChange={(e) => setResolutions((d) => ({ ...d, [selected.id]: e.target.value }))}
                      placeholder="Your response to this question…"
                      className="mt-1 w-full rounded border border-slate-300 p-2 text-sm"
                    />
                  </div>
                  <div className="flex justify-end">
                    <button
                      onClick={() => resolve(selected.id)}
                      disabled={busy || !(resolutions[selected.id] || '').trim()}
                      className="rounded bg-rose-700 text-white text-sm px-3 py-1 hover:bg-rose-800 disabled:bg-slate-300"
                    >
                      Resolve & archive
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="text-sm text-slate-500 border border-dashed rounded-lg p-6 text-center">
              Select an escalation to see full context.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Directory({ me }) {
  const [rows, setRows] = useState([])
  const [busy, setBusy] = useState({})
  const [err, setErr] = useState('')
  const [notice, setNotice] = useState('')

  const refresh = () => {
    adminDirectory().then(setRows).catch((e) => setErr(e.message))
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [])

  const requestReview = async (sme_id, sme_name) => {
    const message = window.prompt(
      `Request a knowledge review from ${sme_name}. Optional message:`,
      'Please review your knowledge entries for accuracy.',
    )
    if (message === null) return
    setBusy((b) => ({ ...b, [sme_id]: true }))
    setErr(''); setNotice('')
    try {
      await adminRequestReview(sme_id, me.id, message || null)
      setNotice(`Review request sent to ${sme_name}.`)
      refresh()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy((b) => ({ ...b, [sme_id]: false }))
    }
  }

  return (
    <div className="space-y-3">
      {err && <div className="text-sm text-rose-600">{err}</div>}
      {notice && <div className="text-sm text-emerald-700">{notice}</div>}
      {rows.map((g, i) => (
        <div key={i} className="bg-white border rounded-lg p-4">
          <div className="font-semibold text-slate-800">{g.subject_name}</div>
          {g.description && <div className="text-xs text-slate-500 mb-2">{g.description}</div>}
          <ul className="text-sm text-slate-700 mt-2 divide-y">
            {g.smes.map((s) => (
              <li key={s.id} className="flex items-center justify-between py-2 gap-3">
                <div className="min-w-0">
                  <div className="font-medium text-slate-800 truncate">
                    {s.name}
                    {s.expertise_area && <span className="text-slate-500 font-normal"> — {g.subject_name} ({s.expertise_area})</span>}
                  </div>
                  {s.contact_info && <div className="text-xs text-slate-500 truncate">{s.contact_info}</div>}
                  {s.review_requested_at && (
                    <div className="text-xs text-amber-700">Review request pending since {new Date(s.review_requested_at).toLocaleDateString()}</div>
                  )}
                </div>
                <button
                  onClick={() => requestReview(s.id, s.name)}
                  disabled={!!busy[s.id]}
                  className="text-xs px-2 py-1 rounded border border-rose-300 text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                >
                  {busy[s.id] ? 'Sending…' : 'Request Review'}
                </button>
              </li>
            ))}
            {g.smes.length === 0 && <li className="text-xs text-slate-400 py-2">No SMEs assigned.</li>}
          </ul>
        </div>
      ))}
    </div>
  )
}
