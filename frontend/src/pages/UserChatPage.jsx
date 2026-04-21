import { useEffect, useState } from 'react'
import ChatWindow from '../components/ChatWindow'
import { query, queryHistory } from '../api'

export default function UserChatPage() {
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
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
    }).catch(() => {})
  }, [])

  const onSend = async (text) => {
    setMessages((m) => [...m, { role: 'user', content: text }])
    setBusy(true)
    try {
      const r = await query(text)
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
    <div className="h-full max-w-3xl mx-auto flex flex-col">
      <div className="px-6 pt-4 pb-2">
        <h2 className="text-lg font-semibold text-slate-800">Ask a question</h2>
        <p className="text-xs text-slate-500">Thoth will route your question to the right subject agent.</p>
      </div>
      <div className="flex-1 min-h-0">
        <ChatWindow
          messages={messages}
          onSend={onSend}
          busy={busy}
          placeholder="e.g. How do I submit an expense report?"
        />
      </div>
    </div>
  )
}
