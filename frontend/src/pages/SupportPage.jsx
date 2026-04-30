import { useEffect } from 'react'
import RoleHeader from '../components/RoleHeader'

export default function SupportPage() {
  // Distinct title so launch.sh's wmctrl pass can find this window
  useEffect(() => { document.title = 'Thoth — Support' }, [])

  return (
    <div className="flex flex-col h-full">
      <RoleHeader role="support" />
      <div className="flex-1 overflow-auto flex items-center justify-center p-8">
        <div className="max-w-md text-center bg-white border rounded-xl p-8 shadow-sm">
          <div className="text-2xl font-semibold text-slate-800 mb-2">Support View</div>
          <div className="text-sm text-slate-500">
            Coming soon. This window will host customer-support tooling — escalation triage, response templates, and SME hand-offs.
          </div>
        </div>
      </div>
    </div>
  )
}
