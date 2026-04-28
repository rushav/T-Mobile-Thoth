import { useEffect, useRef, useState } from 'react'
import ChatWindow from '../components/ChatWindow'
import RoleHeader from '../components/RoleHeader'
import { query, queryHistory, queryWithFile, currentProfile } from '../api'

const MAX_FILE_BYTES = 5 * 1024 * 1024
const ACCEPT = '.pdf,.docx,.txt,.md,.png,.jpg,.jpeg'

export default function UserChatPage() {
  const [profile, setLocalProfile] = useState(currentProfile('user'))
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState(null) // { file, name } before send
  const [pendingErr, setPendingErr] = useState('')
  const fileRef = useRef(null)

  // Reload history whenever the active user changes.
  useEffect(() => {
    if (!profile) { setMessages([]); return }
    queryHistory().then((rows) => {
      const hist = []
      for (const r of [...rows].reverse()) {
        hist.push({ role: 'user', content: r.question })
        if (r.answer) {
          hist.push({
            role: r.status === 'escalated' ? 'system' : 'assistant',
            content: r.answer,
            subject: r.subject_name || undefined,
            status: r.status,
          })
        }
      }
      setMessages(hist)
    }).catch(() => setMessages([]))
  }, [profile?.id])

  const onPickFile = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setPendingErr('')
    if (f.size > MAX_FILE_BYTES) {
      setPendingErr(`"${f.name}" is ${(f.size / 1024 / 1024).toFixed(1)} MB — max is 5 MB.`)
      if (fileRef.current) fileRef.current.value = ''
      return
    }
    setPending({ file: f, name: f.name })
  }

  const clearPending = () => {
    setPending(null)
    setPendingErr('')
    if (fileRef.current) fileRef.current.value = ''
  }

  const onSend = async (text) => {
    const attachedAtSendTime = pending  // capture before clearing
    setMessages((m) => [...m, {
      role: 'user',
      content: text,
      attachment: attachedAtSendTime ? { filename: attachedAtSendTime.name } : undefined,
    }])
    clearPending()
    setBusy(true)
    try {
      const r = attachedAtSendTime
        ? await queryWithFile(text, attachedAtSendTime.file)
        : await query(text)
      if (r.status === 'answered') {
        setMessages((m) => [...m, {
          role: 'assistant',
          content: r.answer,
          subject: r.subject,
          confidence: r.confidence,
          status: r.status,
        }])
      } else if (r.status === 'clarifying') {
        setMessages((m) => [...m, {
          role: 'assistant',
          content: r.question,
          status: 'clarifying',
          confidence: r.confidence,
        }])
      } else if (r.status === 'escalated') {
        setMessages((m) => [...m, {
          role: 'system',
          content: 'Connecting to admin… ' + r.message,
          status: 'escalated',
        }])
      }
    } catch (e) {
      setMessages((m) => [...m, { role: 'system', content: `Error: ${e.message}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <RoleHeader role="user" onProfileChange={setLocalProfile} />
      {!profile ? (
        <div className="flex-1 flex items-center justify-center text-sm text-slate-500">
          Pick or create a user profile in the header to start.
        </div>
      ) : (
        <div className="flex-1 min-h-0 max-w-3xl w-full mx-auto flex flex-col">
          <div className="px-6 pt-4 pb-2">
            <h2 className="text-lg font-semibold text-slate-800">Ask a question</h2>
            <p className="text-xs text-slate-500">Thoth will route your question to the right subject agent.</p>
          </div>
          <div className="flex-1 min-h-0 flex flex-col">
            <ChatWindow
              messages={messages}
              onSend={onSend}
              busy={busy}
              placeholder="e.g. How do I make pour-over coffee?"
              composerExtras={
                <>
                  <input
                    ref={fileRef}
                    type="file"
                    accept={ACCEPT}
                    onChange={onPickFile}
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => fileRef.current?.click()}
                    title="Attach a file (PDF, docx, txt, image — max 5 MB)"
                    className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                  >
                    {/* Paperclip */}
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21.44 11.05l-9.19 9.19a6 6 0 1 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 1 1-2.83-2.83l8.49-8.49"/>
                    </svg>
                  </button>
                </>
              }
              composerAbove={
                (pending || pendingErr) && (
                  <div className="px-3 pt-2">
                    {pending && (
                      <span className="inline-flex items-center gap-2 text-xs bg-slate-100 border border-slate-200 rounded-full pl-3 pr-1 py-1 text-slate-700">
                        <FileGlyph />
                        <span className="truncate max-w-[16rem]">{pending.name}</span>
                        <button onClick={clearPending} className="rounded-full hover:bg-slate-200 w-5 h-5 inline-flex items-center justify-center" aria-label="Remove">
                          ×
                        </button>
                      </span>
                    )}
                    {pendingErr && <div className="text-xs text-rose-600 mt-1">{pendingErr}</div>}
                  </div>
                )
              }
            />
          </div>
        </div>
      )}
    </div>
  )
}

function FileGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  )
}
