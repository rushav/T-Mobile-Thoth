import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble'

export default function ChatWindow({
  messages,
  onSend,
  placeholder = 'Type your message…',
  disabled,
  busy,
  composerExtras,
  composerAbove,
}) {
  const [text, setText] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages])

  const submit = (e) => {
    e.preventDefault()
    const t = text.trim()
    if (!t) return
    setText('')
    onSend(t)
  }

  return (
    <div className="flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-auto px-4 py-4 bg-slate-50">
        {messages.length === 0 && (
          <div className="text-center text-sm text-slate-400 mt-10">Start the conversation…</div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} {...m} />
        ))}
        {busy && (
          <div className="text-xs text-slate-500 italic mt-2">Thoth is thinking…</div>
        )}
      </div>
      <div className="border-t bg-white">
        {composerAbove}
        <form onSubmit={submit} className="flex items-center gap-2 p-3">
          {composerExtras}
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={placeholder}
            disabled={disabled || busy}
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100"
          />
          <button
            type="submit"
            disabled={disabled || busy || !text.trim()}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:bg-slate-300"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
