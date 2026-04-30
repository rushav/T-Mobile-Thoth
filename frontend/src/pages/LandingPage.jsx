const VIEWS = [
  { path: '/user',    label: 'Open User View',    desc: 'Ask Thoth questions and get answers from subject experts.', tone: 'border-blue-300 hover:border-blue-500 hover:bg-blue-50',   tag: 'bg-blue-100 text-blue-800' },
  { path: '/sme',     label: 'Open SME View',     desc: 'Run knowledge-capture interviews and review pending entries.', tone: 'border-teal-300 hover:border-teal-500 hover:bg-teal-50',   tag: 'bg-teal-100 text-teal-800' },
  { path: '/admin',   label: 'Open Admin View',   desc: 'Approve entries, manage escalations, and direct SMEs.',     tone: 'border-rose-300 hover:border-rose-500 hover:bg-rose-50',   tag: 'bg-rose-100 text-rose-800' },
  { path: '/support', label: 'Open Support View', desc: 'Coming soon — operations + customer support tooling.',      tone: 'border-slate-300 hover:border-slate-500 hover:bg-slate-50', tag: 'bg-slate-200 text-slate-800' },
]

export default function LandingPage() {
  const openAllWindows = () => {
    window.open('/user', '_blank');
    window.open('/sme', '_blank');
    window.open('/admin', '_blank');
    window.open('/support', '_blank');
  };

  return (
    <div className="min-h-full p-8 flex flex-col items-center">
      <div className="w-full max-w-4xl">
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <span className="font-semibold">Tip:</span> Run <code className="bg-amber-100 px-1.5 py-0.5 rounded font-mono text-xs">./launch.sh</code> from the project root to open all four views automatically in a 2×2 grid.
        </div>
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-800">Project Thoth</h1>
            <p className="text-sm text-slate-500 mt-1">
              AI-powered SME knowledge capture and retrieval. Open each view in its own tab — they all share the same backend in real time.
            </p>
          </div>
          <button
            onClick={openAllWindows}
            className="shrink-0 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium px-4 py-2 transition"
          >
            Relaunch All Windows
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {VIEWS.map((v) => (
            <a
              key={v.path}
              href={v.path}
              target="_blank"
              rel="noreferrer"
              className={`block rounded-xl border-2 ${v.tone} bg-white p-5 transition`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs uppercase tracking-wider px-2 py-0.5 rounded ${v.tag}`}>{v.path}</span>
              </div>
              <div className="text-lg font-semibold text-slate-800">{v.label}</div>
              <div className="text-sm text-slate-500 mt-1">{v.desc}</div>
              <div className="text-xs text-slate-400 mt-3">Opens in a new tab ↗</div>
            </a>
          ))}
        </div>
        <div className="text-xs text-slate-400 mt-6">
          Tip: keep all four tabs open during a demo. SME approvals flow into the admin window within ~5 seconds.
        </div>
      </div>
    </div>
  )
}
