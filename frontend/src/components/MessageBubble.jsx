import ReactMarkdown from 'react-markdown'
import SubjectBadge from './SubjectBadge'

const markdownComponents = {
  p: ({ node, ...props }) => <p className="leading-relaxed" {...props} />,
  ul: ({ node, ...props }) => <ul className="list-disc ml-5 my-1 space-y-0.5" {...props} />,
  ol: ({ node, ...props }) => <ol className="list-decimal ml-5 my-1 space-y-0.5" {...props} />,
  h1: ({ node, ...props }) => <h1 className="text-base font-bold mt-2 mb-1" {...props} />,
  h2: ({ node, ...props }) => <h2 className="text-sm font-bold mt-2 mb-1" {...props} />,
  h3: ({ node, ...props }) => <h3 className="text-sm font-semibold mt-2 mb-1" {...props} />,
  strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
  em: ({ node, ...props }) => <em className="italic" {...props} />,
  code: ({ node, inline, ...props }) => inline
    ? <code className="rounded bg-slate-100 text-rose-600 px-1 py-0.5 text-[0.85em]" {...props} />
    : <code className="block rounded bg-slate-100 p-2 text-[0.85em] overflow-auto" {...props} />,
  blockquote: ({ node, ...props }) => <blockquote className="border-l-2 border-slate-300 pl-3 italic text-slate-700" {...props} />,
  a: ({ node, ...props }) => <a className="text-indigo-700 underline" target="_blank" rel="noreferrer" {...props} />,
}

function FileGlyph({ className = '' }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  )
}

export default function MessageBubble({ role, content, subject, confidence, status, attachment }) {
  const isUser = role === 'user'
  const isSystem = role === 'system'
  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} mb-3`}>
      <div className={[
        'max-w-[75%] rounded-2xl px-4 py-2 text-sm',
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
        <div className={isUser ? 'whitespace-pre-wrap' : 'prose-sm'}>
          {isUser
            ? content
            : <ReactMarkdown components={markdownComponents}>{content || ''}</ReactMarkdown>}
        </div>
      </div>
      {isUser && attachment?.filename && (
        <div className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500">
          <FileGlyph className="text-slate-400" />
          <span className="truncate max-w-[16rem]">{attachment.filename}</span>
        </div>
      )}
    </div>
  )
}
