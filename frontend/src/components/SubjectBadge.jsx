export default function SubjectBadge({ subject, confidence }) {
  if (!subject) return null
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded bg-indigo-100 text-indigo-800 border border-indigo-200">
      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
      {subject}
      {confidence != null && <span className="text-indigo-500 opacity-70">· {(confidence * 100).toFixed(0)}%</span>}
    </span>
  )
}
