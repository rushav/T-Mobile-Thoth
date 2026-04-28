import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

export default function ReviewPanel({ synthesis, onApprove, onReject, onRequestChanges, busy, revising }) {
  const [feedback, setFeedback] = useState('')

  const submitChanges = () => {
    onRequestChanges(feedback)
    setFeedback('')
  }

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div>
        <h3 className="font-semibold text-slate-800 mb-2 flex items-center gap-2">
          Thoth's synthesis
          {revising && <span className="text-xs font-normal text-amber-700 inline-flex items-center gap-1">
            <span className="inline-block w-3 h-3 border-2 border-amber-300 border-t-amber-700 rounded-full animate-spin" />
            Revising…
          </span>}
        </h3>
        <div className={`text-sm text-slate-700 bg-slate-50 border rounded p-3 max-h-96 overflow-auto ${revising ? 'opacity-60' : ''}`}>
          <ReactMarkdown>{synthesis || ''}</ReactMarkdown>
        </div>
      </div>
      <div>
        <label className="text-sm text-slate-600">Feedback (required for "Request changes")</label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          rows={3}
          className="mt-1 w-full rounded border border-slate-300 p-2 text-sm"
          placeholder="What should Thoth revise? Be specific."
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          disabled={busy}
          className="px-4 py-2 rounded bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 disabled:bg-slate-300"
        >
          Approve
        </button>
        <button
          onClick={submitChanges}
          disabled={busy || !feedback.trim()}
          className="px-4 py-2 rounded bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 disabled:bg-slate-300"
        >
          Request changes
        </button>
        <button
          onClick={onReject}
          disabled={busy}
          className="px-4 py-2 rounded bg-rose-600 text-white text-sm font-medium hover:bg-rose-700 disabled:bg-slate-300"
        >
          Reject
        </button>
      </div>
    </div>
  )
}
