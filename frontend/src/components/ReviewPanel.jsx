import { useState } from 'react'

export default function ReviewPanel({ synthesis, onApprove, onReject, onRequestChanges, busy }) {
  const [feedback, setFeedback] = useState('')

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div>
        <h3 className="font-semibold text-slate-800 mb-2">Thoth's synthesis</h3>
        <div className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 border rounded p-3 max-h-96 overflow-auto">
          {synthesis}
        </div>
      </div>
      <div>
        <label className="text-sm text-slate-600">Feedback (optional, for "Request changes")</label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          rows={3}
          className="mt-1 w-full rounded border border-slate-300 p-2 text-sm"
          placeholder="What should Thoth revise?"
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
          onClick={() => onRequestChanges(feedback)}
          disabled={busy}
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
