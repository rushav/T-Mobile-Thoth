import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import ChatWindow from '../components/ChatWindow'
import ReviewPanel from '../components/ReviewPanel'
import RoleHeader from '../components/RoleHeader'
import {
  currentProfile, setProfile,
  getProfile, getProfileSubjects, createSubject,
  startInterview, sendInterviewMessage,
  synthesizeInterview, reviewInterview, uploadFile,
  pendingForSme, reviewEntry,
  clearReviewRequest,
} from '../api'

const POLL_MS = 5000

export default function SMEDashboardPage() {
  const [me, setMe] = useState(currentProfile('sme'))
  const [tab, setTab] = useState('interview')

  // Distinct title so launch.sh's wmctrl pass can find this window
  useEffect(() => { document.title = 'Thoth — SME' }, [])

  // Poll the active SME's profile so review-request flags appear within 5s
  // even if the admin sets one in another tab.
  useEffect(() => {
    if (!me) return
    let cancelled = false
    const tick = async () => {
      try {
        const p = await getProfile(me.id)
        if (cancelled) return
        setMe(p)
        setProfile('sme', p)
      } catch {}
    }
    tick()
    const id = setInterval(tick, POLL_MS)
    return () => { cancelled = true; clearInterval(id) }
  }, [me?.id])

  const dismissReview = async () => {
    try {
      const p = await clearReviewRequest(me.id)
      setMe(p)
      setProfile('sme', p)
    } catch {}
  }

  return (
    <div className="flex flex-col h-full">
      <RoleHeader role="sme" onProfileChange={setMe} />
      {!me ? (
        <div className="flex-1 flex items-center justify-center text-sm text-slate-500">
          Pick or create an SME profile in the header to start.
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <div className="max-w-5xl mx-auto px-6 py-4">
            {me.review_requested_at && (
              <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3 flex items-start justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold text-amber-900">Review request from admin</div>
                  <div className="text-sm text-amber-800 mt-0.5">
                    {me.review_request_message || 'Admin has requested you review your knowledge entries for accuracy.'}
                  </div>
                  <div className="text-xs text-amber-700 mt-1">
                    Requested {new Date(me.review_requested_at).toLocaleString()}
                  </div>
                </div>
                <button onClick={dismissReview} className="text-xs px-2 py-1 rounded border border-amber-300 hover:bg-amber-100">Dismiss</button>
              </div>
            )}

            <div className="flex gap-4 border-b mb-4">
              <TabButton active={tab === 'interview'} onClick={() => setTab('interview')}>Interview</TabButton>
              <TabButton active={tab === 'reviews'} onClick={() => setTab('reviews')}>Pending Reviews</TabButton>
            </div>
            {tab === 'interview' ? <InterviewTab me={me} /> : <ReviewsTab me={me} />}
          </div>
        </div>
      )}
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={[
        'px-4 py-2 text-sm font-medium border-b-2 -mb-px',
        active ? 'border-teal-600 text-teal-700' : 'border-transparent text-slate-500 hover:text-slate-800',
      ].join(' ')}
    >{children}</button>
  )
}

function InterviewTab({ me }) {
  const [mySubjects, setMySubjects] = useState([])
  const [subjectId, setSubjectId] = useState('')
  const [mode, setMode] = useState('structured')
  const [interviewId, setInterviewId] = useState(null)
  const [messages, setMessages] = useState([])
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [synthesizing, setSynthesizing] = useState(false)
  const [synthesis, setSynthesis] = useState(null)
  const [status, setStatus] = useState('idle') // idle | chatting | reviewing | done
  const fileRef = useRef(null)
  const [err, setErr] = useState('')

  // New-subject form
  const [showNewSubject, setShowNewSubject] = useState(false)
  const [newSubjectName, setNewSubjectName] = useState('')
  const [newSubjectExpertise, setNewSubjectExpertise] = useState('')
  const [newSubjectDesc, setNewSubjectDesc] = useState('')

  const refreshMySubjects = async () => {
    try {
      const subs = await getProfileSubjects(me.id)
      setMySubjects(subs)
      return subs
    } catch (e) {
      setErr(e.message)
      return []
    }
  }

  useEffect(() => {
    refreshMySubjects()
    // Reset interview state when the active SME changes.
    setInterviewId(null); setMessages([]); setFiles([]); setSynthesis(null); setStatus('idle'); setSubjectId('')
  }, [me.id])

  const start = async () => {
    if (!subjectId) return
    setErr('')
    setBusy(true)
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
      setStatus('done')
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  const reject = async () => {
    setBusy(true); setErr('')
    try {
      await reviewInterview(interviewId, 'reject')
      setStatus('done')
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  const requestChanges = async (feedback) => {
    setSynthesizing(true); setErr('')
    try {
      const r = await reviewInterview(interviewId, 'request_changes', feedback)
      if (r.synthesis) setSynthesis(r.synthesis)
      setStatus('reviewing')
    } catch (e) { setErr(e.message) } finally { setSynthesizing(false) }
  }

  const reset = () => {
    setInterviewId(null); setMessages([]); setFiles([]); setSynthesis(null); setStatus('idle'); setSubjectId('')
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
      try {
        const p = await getProfile(me.id)
        setProfile('sme', p)
      } catch {}
      setSubjectId(String(created.id))
      setShowNewSubject(false)
      setNewSubjectName(''); setNewSubjectExpertise(''); setNewSubjectDesc('')
    } catch (e) { setErr(e.message) }
  }

  if (status === 'idle') {
    return (
      <div className="bg-white border rounded-lg p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Start a new interview</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="block text-sm text-slate-700">Subject</label>
            <button
              type="button"
              onClick={() => setShowNewSubject((v) => !v)}
              className="text-sm text-teal-700 hover:text-teal-900"
            >
              {showNewSubject ? 'Cancel' : '+ New subject'}
            </button>
          </div>
          {!showNewSubject && (
            <select
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
              className="w-full rounded border border-slate-300 p-2 text-sm"
            >
              <option value="">— pick one of your subjects —</option>
              {mySubjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          )}
          {!showNewSubject && mySubjects.length === 0 && (
            <div className="text-xs text-slate-500">
              You don't have any subjects yet. Create one to start an interview.
            </div>
          )}

          {showNewSubject && (
            <form onSubmit={submitNewSubject} className="space-y-2 border rounded-md p-3 bg-slate-50">
              <div>
                <label className="text-xs text-slate-600">Subject name</label>
                <input value={newSubjectName} onChange={(e) => setNewSubjectName(e.target.value)} required
                  placeholder="e.g. Climbing"
                  className="mt-1 w-full rounded border border-slate-300 p-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-slate-600">Your expertise within this subject</label>
                <input value={newSubjectExpertise} onChange={(e) => setNewSubjectExpertise(e.target.value)}
                  placeholder="e.g. Sport Climbing"
                  className="mt-1 w-full rounded border border-slate-300 p-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-slate-600">Short description (optional)</label>
                <input value={newSubjectDesc} onChange={(e) => setNewSubjectDesc(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 p-2 text-sm" />
              </div>
              <button type="submit" className="rounded bg-teal-700 text-white px-3 py-1.5 text-sm hover:bg-teal-800">
                Create & select
              </button>
            </form>
          )}

          <div>
            <label className="block text-sm text-slate-700 mb-1">Interview style</label>
            <div className="grid grid-cols-2 gap-2">
              <label className={`flex items-start gap-2 rounded border p-2 cursor-pointer ${mode === 'structured' ? 'border-teal-600 bg-teal-50' : 'border-slate-300'}`}>
                <input type="radio" name="mode" value="structured" checked={mode === 'structured'} onChange={() => setMode('structured')} className="mt-1" />
                <span>
                  <div className="text-sm font-medium text-slate-800">Structured</div>
                  <div className="text-xs text-slate-500">Thoth walks you through key facts → common questions → mistakes → escalation triggers.</div>
                </span>
              </label>
              <label className={`flex items-start gap-2 rounded border p-2 cursor-pointer ${mode === 'freeform' ? 'border-teal-600 bg-teal-50' : 'border-slate-300'}`}>
                <input type="radio" name="mode" value="freeform" checked={mode === 'freeform'} onChange={() => setMode('freeform')} className="mt-1" />
                <span>
                  <div className="text-sm font-medium text-slate-800">Freeform</div>
                  <div className="text-xs text-slate-500">Share what you know; Thoth follows up only when something is unclear.</div>
                </span>
              </label>
            </div>
          </div>

          {err && <div className="text-sm text-rose-600">{err}</div>}
          <button
            onClick={start}
            disabled={!subjectId || busy}
            className="rounded bg-teal-700 text-white px-4 py-2 text-sm font-medium hover:bg-teal-800 disabled:bg-slate-300"
          >
            Start interview
          </button>
        </div>
      </div>
    )
  }

  if (status === 'done') {
    return (
      <div className="bg-white border rounded-lg p-6 text-center">
        <div className="text-lg font-semibold text-slate-800 mb-2">Interview complete</div>
        <p className="text-sm text-slate-500 mb-4">Your contribution is queued for admin approval.</p>
        <button onClick={reset} className="rounded bg-teal-700 text-white px-4 py-2 text-sm font-medium hover:bg-teal-800">Start another</button>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 bg-white border rounded-lg overflow-hidden h-[70vh] flex flex-col">
        <ChatWindow
          messages={messages}
          onSend={onSend}
          busy={busy}
          disabled={status !== 'chatting'}
          placeholder="Share what you know…"
        />
      </div>
      <div className="space-y-4">
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-slate-800 mb-2">Supporting files</h3>
          <input ref={fileRef} type="file" onChange={onUpload} accept=".pdf,.docx,.txt,.md" className="text-sm" />
          <ul className="mt-3 space-y-1 text-sm text-slate-700">
            {files.map((f) => (
              <li key={f.id} className="flex items-center justify-between">
                <span>{f.filename}</span>
                <span className="text-xs text-slate-400">{f.extracted_chars} chars</span>
              </li>
            ))}
            {files.length === 0 && <li className="text-xs text-slate-400">No files uploaded.</li>}
          </ul>
        </div>

        {status === 'chatting' && (
          <button
            onClick={generate}
            disabled={synthesizing || messages.length < 2}
            className="w-full rounded bg-emerald-600 text-white px-4 py-2 text-sm font-medium hover:bg-emerald-700 disabled:bg-slate-300 flex items-center justify-center gap-2"
          >
            {synthesizing && <Spinner />}
            {synthesizing ? 'Generating summary…' : 'Generate summary'}
          </button>
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

function Spinner() {
  return (
    <span className="inline-block w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
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

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [me.id])

  const act = async (entry_id, action) => {
    setBusy(true)
    try {
      await reviewEntry(entry_id, action, me.id)
      await refresh()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3">
      {err && <div className="text-sm text-rose-600">{err}</div>}
      {rows.length === 0 && <div className="text-sm text-slate-500">No pending entries for your subjects.</div>}
      {rows.map((r) => (
        <div key={r.id} className="bg-white border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="font-semibold text-slate-800">{r.title}</div>
              <div className="text-xs text-slate-500">{r.subject_name} · contributed by {r.contributor_name || 'unknown'}</div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => act(r.id, 'approve')} disabled={busy} className="rounded bg-emerald-600 text-white text-sm px-3 py-1 hover:bg-emerald-700">Approve</button>
              <button onClick={() => act(r.id, 'reject')} disabled={busy} className="rounded bg-rose-600 text-white text-sm px-3 py-1 hover:bg-rose-700">Reject</button>
            </div>
          </div>
          <div className="text-sm text-slate-700 bg-slate-50 border rounded p-3 max-h-64 overflow-auto">
            <ReactMarkdown>{r.content || ''}</ReactMarkdown>
          </div>
        </div>
      ))}
    </div>
  )
}
