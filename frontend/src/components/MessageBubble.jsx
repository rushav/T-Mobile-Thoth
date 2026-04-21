import SubjectBadge from './SubjectBadge'

export default function MessageBubble({ role, content, subject, confidence, status }) {
  const isUser = role === 'user'
  const isSystem = role === 'system'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={[
        'max-w-[75%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap',
        isUser ? 'bg-blue-600 text-white'
          : isSystem ? 'bg-amber-100 text-amber-900 border border-amber-200'
          : 'bg-white text-slate-800 border border-slate-200 shadow-sm'
      ].join(' ')}>
        {!isUser && (subject || status) && (
          <div className="mb-1 flex items-center gap-2">
            {subject && <SubjectBadge subject={subject} confidence={confidence} />}
            {status === 'clarifying' && <span className="text-xs text-amber-700">Clarifying</span>}
            {status === 'escalated' && <span className="text-xs text-rose-700">Escalated</span>}
          </div>
        )}
        <div>{content}</div>
      </div>
    </div>
  )
}
