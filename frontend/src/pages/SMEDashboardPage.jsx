import { useEffect, useRef, useState } from 'react'
import ChatWindow from '../components/ChatWindow'
import ReviewPanel from '../components/ReviewPanel'
import TopBar from '../components/TopBar'
import {
  getProfile, getProfileSubjects, createSubject,
  startInterview, sendInterviewMessage,
  synthesizeInterview, reviewInterview, uploadFile, listInterviews,
  pendingForSme, reviewEntry,
  clearReviewRequest,
} from '../api'
import { useAuth, setUser } from '../auth'

const PINK = '#E20074'

export default function SMEDashboardPage() {
  const me = useAuth()
  const [meFull, setMeFull] = useState(me)
  const [tab, setTab] = useState('interview')
  const [selectedInterview, setSelectedInterview] = useState(null)

  useEffect(() => { document.title = 'Thoth — SME' }, [])

  // Pull the latest profile once on mount (review-request flag, etc.). No
  // polling — single window, refresh manually if needed.
  useEffect(() => {
    if (!me?.id) return
    let cancelled = false
    getProfile(me.id).then(p => {
      if (cancelled) return
      setMeFull(p)
      setUser(p)
    }).catch(() => {})
    return () => { cancelled = true }
  }, [me?.id])

  const dismissReview = async () => {
    try {
      const p = await clearReviewRequest(meFull.id)
      setMeFull(p)
      setUser(p)
    } catch {}
  }

  if (!meFull) return null

  return (
    <div className="flex flex-col h-full bg-white">
      <TopBar />
      <div className="flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto px-6 py-4">
          {meFull.review_requested_at && (
            <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3 flex items-start justify-between gap-4">
              <div>
                <div className="text-sm font-semibold text-amber-900">Review request from admin</div>
                <div className="text-sm text-amber-800 mt-0.5">
                  {meFull.review_request_message || 'Admin has requested you review your knowledge entries for accuracy.'}
                </div>
                <div className="text-xs text-amber-700 mt-1">
                  Requested {new Date(meFull.review_requested_at).toLocaleString()}
                </div>
              </div>
              <button onClick={dismissReview} className="text-xs px-2 py-1 rounded border border-amber-300 hover:bg-amber-100">Dismiss</button>
            </div>
          )}

          <div className="flex gap-4 border-b border-gray-200 mb-4">
            <TabButton active={tab === 'interview'} onClick={() => setTab('interview')}>Interview</TabButton>
            <TabButton active={tab === 'reviews'} onClick={() => setTab('reviews')}>Pending Reviews</TabButton>
            <TabButton active={tab === 'history'} onClick={() => setTab('history')}>My Interviews</TabButton>
          </div>
          {tab === 'interview' && (
            <InterviewTab
              key={selectedInterview?.id ?? 'new'}
              me={meFull}
              initialInterview={selectedInterview}
              onNewInterview={() => { setSelectedInterview(null); setTab('interview') }}
            />
          )}
          {tab === 'reviews' && <ReviewsTab me={meFull} />}
          {tab === 'history' && (
            <HistoryTab
              me={meFull}
              onSelectInterview={(iv) => { setSelectedInterview(iv); setTab('interview') }}
            />
          )}
        </div>
      </div>
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors"
      style={{
        borderColor: active ? PINK : 'transparent',
        color: active ? PINK : '#64748b',
      }}
    >{children}</button>
  )
}

function InterviewTab({ me, initialInterview = null, onNewInterview }) {
  const [mySubjects, setMySubjects] = useState([])
  const [mode, setMode] = useState('structured')
  const [interviewId, setInterviewId] = useState(() => initialInterview?.id ?? null)
  const [messages, setMessages] = useState(() => initialInterview?.messages ?? [])
  const [files, setFiles] = useState(() => initialInterview?.files ?? [])
  const [busy, setBusy] = useState(false)
  const [synthesizing, setSynthesizing] = useState(false)
  const [synthesis, setSynthesis] = useState(() => initialInterview?.synthesis ?? '')
  const [status, setStatus] = useState(() => {
    if (!initialInterview) return 'idle'
    if (!initialInterview.synthesis) return 'chatting'
    if (initialInterview.synthesis_status === 'post_review_chat') return 'post_review_chatting'
    if (['draft', 'pending_review'].includes(initialInterview.synthesis_status)) return 'reviewing'
    if (initialInterview.synthesis_status === 'approved') return 'done_approved'
    if (initialInterview.synthesis_status === 'rejected') return 'done_rejected'
    return 'reviewing'
  })
  const [subjectId, setSubjectId] = useState(() =>
    initialInterview ? String(initialInterview.subject_id) : ''
  )
  const fileRef = useRef(null)
  const [err, setErr] = useState('')

  const [showNewSubject, setShowNewSubject] = useState(false)
  const [newSubjectName, setNewSubjectName] = useState('')
  const [newSubjectExpertise, setNewSubjectExpertise] = useState('')
  const [newSubjectDesc, setNewSubjectDesc] = useState('')

  const refreshMySubjects = async () => {
    try {
      const subs = await getProfileSubjects(me.id)
      setMySubjects(subs)
      return subs
    } catch (e) { setErr(e.message); return [] }
  }

  useEffect(() => { refreshMySubjects() }, [me.id])

  const start = async () => {
    if (!subjectId) return
    setErr(''); setBusy(true)
    try {
      const r = await startInterview(me.id, Number(subjectId), mode)
      setInterviewId(r.interview_id)
      setMessages([{ role: 'assistant', content: r.opening_message }])
      setStatus('chatting')
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  const onSend = async (text) => {
    setMessages((m) => [...m, { role: 'user', content: text }])
    setBusy(true)
    try {
      const r = await sendInterviewMessage(interviewId, text)
      setMessages((m) => [...m, { role: 'assistant', content: r.reply }])
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  const onUpload = async (e) => {
    const f = e.target.files?.[0]
    if (!f || !interviewId) return
    setBusy(true); setErr('')
    try {
      const r = await uploadFile(f, { interview_id: interviewId })
      setFiles((fs) => [...fs, r])
    } catch (e) { setErr(e.message) } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const generate = async () => {
    setSynthesizing(true); setErr('')
    try {
      const r = await synthesizeInterview(interviewId)
      setSynthesis(r.synthesis)
      setStatus('reviewing')
    } catch (e) { setErr(e.message) } finally { setSynthesizing(false) }
  }

  const approve = async () => {
    setBusy(true); setErr('')
    try {
      await reviewInterview(interviewId, 'approve')
      setStatus('done_approved')
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  const reject = async () => {
    setBusy(true); setErr('')
    try {
      await reviewInterview(interviewId, 'reject')
      setStatus('done_rejected')
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  const requestChanges = async (feedback) => {
    setBusy(true); setErr('')
    try {
      const r = await reviewInterview(interviewId, 'request_changes', feedback)
      setMessages(r.messages)
      setStatus('post_review_chatting')
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  const regenerate = async () => {
    setSynthesizing(true); setErr('')
    try {
      const r = await synthesizeInterview(interviewId)
      setSynthesis(r.synthesis)
      setStatus('reviewing')
    } catch (e) { setErr(e.message) } finally { setSynthesizing(false) }
  }

  const submitNewSubject = async (e) => {
    e.preventDefault()
    if (!newSubjectName.trim()) return
    setErr('')
    try {
      const created = await createSubject({
        name: newSubjectName.trim(),
        description: newSubjectDesc.trim() || null,
        sme_id: me.id,
        expertise: newSubjectExpertise.trim() || null,
      })
      await refreshMySubjects()
      try { const p = await getProfile(me.id); setUser(p) } catch {}
      setSubjectId(String(created.id))
      setShowNewSubject(false)
      setNewSubjectName(''); setNewSubjectExpertise(''); setNewSubjectDesc('')
    } catch (e) { setErr(e.message) }
  }

  if (status === 'idle') {
    return (
      <div className="bg-white border border-gray-200 rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Start a new interview</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="block text-sm text-gray-700">Subject</label>
            <button type="button" onClick={() => setShowNewSubject(v => !v)} className="text-sm hover:underline" style={{ color: PINK }}>
              {showNewSubject ? 'Cancel' : '+ New subject'}
            </button>
          </div>
          {!showNewSubject && (
            <select
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
              className="w-full rounded-md border border-gray-300 p-2 text-sm"
            >
              <option value="">— pick one of your subjects —</option>
              {mySubjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          )}
          {!showNewSubject && mySubjects.length === 0 && (
            <div className="text-xs text-gray-500">No subjects assigned yet — create one to start.</div>
          )}

          {showNewSubject && (
            <form onSubmit={submitNewSubject} className="space-y-2 border border-gray-200 rounded-md p-3 bg-gray-50">
              <div>
                <label className="text-xs text-gray-600">Subject name</label>
                <input value={newSubjectName} onChange={e => setNewSubjectName(e.target.value)} required placeholder="e.g. Climbing" className="mt-1 w-full rounded border border-gray-300 p-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-gray-600">Your expertise within this subject</label>
                <input value={newSubjectExpertise} onChange={e => setNewSubjectExpertise(e.target.value)} placeholder="e.g. Sport Climbing" className="mt-1 w-full rounded border border-gray-300 p-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-gray-600">Short description (optional)</label>
                <input value={newSubjectDesc} onChange={e => setNewSubjectDesc(e.target.value)} className="mt-1 w-full rounded border border-gray-300 p-2 text-sm" />
              </div>
              <button type="submit" className="rounded-md text-white px-3 py-1.5 text-sm" style={{ backgroundColor: PINK }}>Create & select</button>
            </form>
          )}

          <div>
            <label className="block text-sm text-gray-700 mb-1">Interview style</label>
            <div className="grid grid-cols-2 gap-2">
              <ModeOption value="structured" active={mode} onChange={setMode} title="Structured" desc="Thoth walks you through key facts → common questions → mistakes → escalation triggers." />
              <ModeOption value="freeform"   active={mode} onChange={setMode} title="Freeform"   desc="Share what you know; Thoth follows up only when something is unclear." />
            </div>
          </div>

          {err && <div className="text-sm text-rose-600">{err}</div>}
          <button onClick={start} disabled={!subjectId || busy} className="rounded-md text-white px-4 py-2 text-sm font-medium disabled:bg-gray-300" style={{ backgroundColor: !subjectId || busy ? undefined : PINK }}>
            Start interview
          </button>
        </div>
      </div>
    )
  }

  if (status === 'done_approved' || status === 'done_rejected') {
    const rejected = status === 'done_rejected'
    return (
      <div className="bg-white border border-gray-200 rounded-2xl p-6 text-center">
        <div className="text-lg font-semibold text-gray-900 mb-2">
          {rejected ? 'Interview rejected' : 'Interview complete'}
        </div>
        <p className={`text-sm mb-4 ${rejected ? 'text-rose-600' : 'text-gray-500'}`}>
          {rejected
            ? 'This entry has been rejected. No further action will be taken.'
            : 'Successfully approved and queued for admin review.'}
        </p>
        <button onClick={onNewInterview} className="rounded-md text-white px-4 py-2 text-sm font-medium" style={{ backgroundColor: PINK }}>+ New Interview</button>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 bg-white border border-gray-200 rounded-2xl overflow-hidden h-[70vh] flex flex-col">
        <ChatWindow
          messages={messages}
          onSend={onSend}
          busy={busy}
          disabled={status !== 'chatting' && status !== 'post_review_chatting'}
          placeholder="Share what you know…"
        />
      </div>
      <div className="space-y-4">
        <div className="bg-white border border-gray-200 rounded-2xl p-4">
          <h3 className="font-semibold text-gray-900 mb-2">Supporting files</h3>
          <input ref={fileRef} type="file" onChange={onUpload} accept=".pdf,.docx,.txt,.md" className="text-sm" />
          <ul className="mt-3 space-y-1 text-sm text-gray-700">
            {files.map(f => (
              <li key={f.id} className="flex items-center justify-between">
                <span>{f.filename}</span>
                <span className="text-xs text-gray-400">{f.extracted_chars} chars</span>
              </li>
            ))}
            {files.length === 0 && <li className="text-xs text-gray-400">No files uploaded.</li>}
          </ul>
        </div>

        {status === 'chatting' && (
          <button
            onClick={generate}
            disabled={synthesizing || messages.length < 2}
            className="w-full rounded-md text-white px-4 py-2 text-sm font-medium disabled:bg-gray-300 flex items-center justify-center gap-2"
            style={{ backgroundColor: synthesizing || messages.length < 2 ? undefined : '#0f172a' }}
          >
            {synthesizing && <Spinner />}
            {synthesizing ? 'Generating summary…' : 'Generate summary'}
          </button>
        )}
        {status === 'post_review_chatting' && (
          <div className="bg-white border border-gray-200 rounded-2xl p-4 space-y-3">
            <p className="text-sm text-gray-600">Add any missing context above, then regenerate when ready.</p>
            <button
              onClick={regenerate}
              disabled={synthesizing}
              className="w-full rounded-md text-white px-4 py-2 text-sm font-medium disabled:bg-gray-300 flex items-center justify-center gap-2"
              style={{ backgroundColor: synthesizing ? undefined : '#0f172a' }}
            >
              {synthesizing && <Spinner />}
              {synthesizing ? 'Regenerating…' : 'Regenerate Summary'}
            </button>
          </div>
        )}
        {err && <div className="text-sm text-rose-600">{err}</div>}

        {status === 'reviewing' && synthesis && (
          <ReviewPanel
            synthesis={synthesis}
            onApprove={approve}
            onReject={reject}
            onRequestChanges={requestChanges}
            busy={busy || synthesizing}
            revising={synthesizing}
          />
        )}
      </div>
    </div>
  )
}

function ModeOption({ value, active, onChange, title, desc }) {
  const selected = active === value
  return (
    <label className={`flex items-start gap-2 rounded-lg border p-2 cursor-pointer ${selected ? 'border-[#E20074] bg-pink-50' : 'border-gray-300'}`}>
      <input type="radio" name="mode" value={value} checked={selected} onChange={() => onChange(value)} className="mt-1" />
      <span>
        <div className="text-sm font-medium text-gray-900">{title}</div>
        <div className="text-xs text-gray-500">{desc}</div>
      </span>
    </label>
  )
}

function Spinner() {
  return <span className="inline-block w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
}

function HistoryTab({ me, onSelectInterview }) {
  const [interviews, setInterviews] = useState([])
  const [busy, setBusy] = useState(true)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!me) return
    setBusy(true); setErr('')
    listInterviews(me.id)
      .then(setInterviews)
      .catch(() => setErr('Failed to load interviews'))
      .finally(() => setBusy(false))
  }, [me?.id])

  const statusLabel = (iv) => {
    if (!iv.synthesis) return { text: 'In Progress', color: 'gray' }
    const map = {
      draft: { text: 'Draft', color: 'yellow' },
      pending_review: { text: 'Pending', color: 'yellow' },
      approved: { text: 'Approved', color: 'green' },
      rejected: { text: 'Rejected', color: 'red' },
    }
    return map[iv.synthesis_status] ?? { text: iv.synthesis_status, color: 'gray' }
  }

  if (busy) return <p className="p-6 text-gray-500">Loading…</p>
  if (err) return <p className="p-6 text-red-500">{err}</p>
  if (!interviews.length) {
    return <p className="p-6 text-gray-500">No interviews yet. Start one from the Interview tab.</p>
  }

  return (
    <div className="overflow-x-auto p-4">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-200">
            <th className="pb-2 pr-4">Date</th>
            <th className="pb-2 pr-4">Subject</th>
            <th className="pb-2 pr-4">Mode</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2">Synthesis Preview</th>
          </tr>
        </thead>
        <tbody>
          {interviews.map(iv => {
            const { text, color } = statusLabel(iv)
            const preview = iv.synthesis
              ? iv.synthesis.slice(0, 80) + (iv.synthesis.length > 80 ? '…' : '')
              : '—'
            const date = iv.created_at
              ? new Date(iv.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
              : '—'
            return (
              <tr key={iv.id} onClick={() => onSelectInterview(iv)} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer">
                <td className="py-2 pr-4 whitespace-nowrap">{date}</td>
                <td className="py-2 pr-4">{iv.subject_name ?? '—'}</td>
                <td className="py-2 pr-4 capitalize">{iv.mode}</td>
                <td className="py-2 pr-4"><span className={`text-${color}-600 font-medium`}>{text}</span></td>
                <td className="py-2 text-gray-500">{preview}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function ReviewsTab({ me }) {
  const [rows, setRows] = useState([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const refresh = async () => {
    setErr('')
    try { setRows(await pendingForSme(me.id)) } catch (e) { setErr(e.message) }
  }

  useEffect(() => { refresh() }, [me.id])

  const act = async (entry_id, action, feedback = undefined) => {
    setBusy(true)
    try {
      await reviewEntry(entry_id, action, me.id, feedback)
      await refresh()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3">
      {err && <div className="text-sm text-rose-600">{err}</div>}
      {rows.length === 0 && <div className="text-sm text-gray-500">No pending entries for your subjects.</div>}
      {rows.map(r => (
        <div key={r.id} className="bg-white border border-gray-200 rounded-2xl p-4">
          <div className="mb-3">
            <div className="font-semibold text-gray-900">{r.title}</div>
            <div className="text-xs text-gray-500">{r.subject_name} · contributed by {r.contributor_name || 'unknown'}</div>
          </div>
          <ReviewPanel
            synthesis={r.content}
            onApprove={() => act(r.id, 'approve')}
            onReject={() => act(r.id, 'reject')}
            onRequestChanges={(feedback) => act(r.id, 'request_changes', feedback)}
            busy={busy}
          />
        </div>
      ))}
    </div>
  )
}
