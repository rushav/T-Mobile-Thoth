import { useEffect, useRef, useState } from 'react'
import ChatWindow from '../components/ChatWindow'
import ReviewPanel from '../components/ReviewPanel'
import {
  currentProfile, listSubjects, startInterview, sendInterviewMessage,
  synthesizeInterview, reviewInterview, uploadFile,
  pendingForSme, reviewEntry,
} from '../api'

export default function SMEDashboardPage() {
  const [tab, setTab] = useState('interview')
  return (
    <div className="max-w-5xl mx-auto px-6 py-4">
      <div className="flex gap-4 border-b mb-4">
        <TabButton active={tab === 'interview'} onClick={() => setTab('interview')}>Interview</TabButton>
        <TabButton active={tab === 'reviews'} onClick={() => setTab('reviews')}>Pending Reviews</TabButton>
      </div>
      {tab === 'interview' ? <InterviewTab /> : <ReviewsTab />}
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={[
        'px-4 py-2 text-sm font-medium border-b-2 -mb-px',
        active ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-800',
      ].join(' ')}
    >{children}</button>
  )
}

function InterviewTab() {
  const me = currentProfile()
  const [subjects, setSubjects] = useState([])
  const [subjectId, setSubjectId] = useState('')
  const [interviewId, setInterviewId] = useState(null)
  const [messages, setMessages] = useState([])
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [synthesis, setSynthesis] = useState(null)
  const [status, setStatus] = useState('idle') // idle | chatting | reviewing | done
  const fileRef = useRef(null)
  const [err, setErr] = useState('')

  useEffect(() => { listSubjects().then(setSubjects).catch(() => {}) }, [])

  const start = async () => {
    if (!subjectId) return
    setErr('')
    setBusy(true)
    try {
      const r = await startInterview(me.id, Number(subjectId))
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
    setBusy(true); setErr('')
    try {
      const r = await synthesizeInterview(interviewId)
      setSynthesis(r.synthesis)
      setStatus('reviewing')
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
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
    setBusy(true); setErr('')
    try {
      await reviewInterview(interviewId, 'request_changes', feedback)
      // Let SME keep talking; regenerate later
      setStatus('chatting')
      setSynthesis(null)
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  const reset = () => {
    setInterviewId(null); setMessages([]); setFiles([]); setSynthesis(null); setStatus('idle'); setSubjectId('')
  }

  if (status === 'idle') {
    return (
      <div className="bg-white border rounded-lg p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Start a new interview</h2>
        <div className="space-y-3">
          <label className="block text-sm text-slate-700">Subject</label>
          <select
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
            className="w-full rounded border border-slate-300 p-2 text-sm"
          >
            <option value="">— pick a subject —</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          {err && <div className="text-sm text-rose-600">{err}</div>}
          <button
            onClick={start}
            disabled={!subjectId || busy}
            className="rounded bg-indigo-600 text-white px-4 py-2 text-sm font-medium hover:bg-indigo-700 disabled:bg-slate-300"
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
        <p className="text-sm text-slate-500 mb-4">Your contribution has been recorded.</p>
        <button onClick={reset} className="rounded bg-indigo-600 text-white px-4 py-2 text-sm font-medium hover:bg-indigo-700">Start another</button>
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
            disabled={busy || messages.length < 2}
            className="w-full rounded bg-emerald-600 text-white px-4 py-2 text-sm font-medium hover:bg-emerald-700 disabled:bg-slate-300"
          >
            Generate summary
          </button>
        )}
        {err && <div className="text-sm text-rose-600">{err}</div>}

        {status === 'reviewing' && synthesis && (
          <ReviewPanel
            synthesis={synthesis}
            onApprove={approve}
            onReject={reject}
            onRequestChanges={requestChanges}
            busy={busy}
          />
        )}
      </div>
    </div>
  )
}

function ReviewsTab() {
  const me = currentProfile()
  const [rows, setRows] = useState([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const refresh = async () => {
    setErr('')
    try { setRows(await pendingForSme(me.id)) } catch (e) { setErr(e.message) }
  }

  useEffect(() => { refresh() }, [])

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
          <div className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 border rounded p-3 max-h-64 overflow-auto">
            {r.content}
          </div>
        </div>
      ))}
    </div>
  )
}
