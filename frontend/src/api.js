const BASE = ''  // Vite proxy forwards /api to :8000

function profileHeaders() {
  const p = currentProfile()
  return p ? { 'X-Profile-Id': String(p.id) } : {}
}

export function currentProfile() {
  try {
    const raw = localStorage.getItem('thoth.profile')
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export function setProfile(p) {
  if (p) localStorage.setItem('thoth.profile', JSON.stringify(p))
  else localStorage.removeItem('thoth.profile')
}

async function handle(res) {
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`
    try { const j = await res.json(); msg = j.detail || msg } catch {}
    throw new Error(msg)
  }
  if (res.status === 204) return null
  return res.json()
}

export async function apiGet(path) {
  const res = await fetch(BASE + path, { headers: { ...profileHeaders() } })
  return handle(res)
}

export async function apiPost(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...profileHeaders() },
    body: body == null ? null : JSON.stringify(body),
  })
  return handle(res)
}

export async function apiUpload(path, formData) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { ...profileHeaders() },
    body: formData,
  })
  return handle(res)
}

// Domain helpers
export const listProfiles = (role) => apiGet(`/api/profiles${role ? `?role=${role}` : ''}`)
export const createProfile = (payload) => apiPost('/api/profiles', payload)
export const login = (profile_id) => apiPost('/api/profiles/login', { profile_id })

export const listSubjects = () => apiGet('/api/subjects')
export const query = (question) => apiPost('/api/query', { question })
export const queryHistory = () => apiGet('/api/query/history')

export const startInterview = (sme_id, subject_id) => apiPost('/api/interviews/start', { sme_id, subject_id })
export const sendInterviewMessage = (id, content) => apiPost(`/api/interviews/${id}/message`, { content })
export const synthesizeInterview = (id) => apiPost(`/api/interviews/${id}/synthesize`)
export const reviewInterview = (id, action, feedback) => apiPost(`/api/interviews/${id}/review`, { action, feedback })
export const getInterview = (id) => apiGet(`/api/interviews/${id}`)

export const pendingForSme = (sme_id) => apiGet(`/api/review/pending?sme_id=${sme_id}`)
export const reviewEntry = (entry_id, action, reviewer_id) => apiPost(`/api/review/${entry_id}`, { action, reviewer_id })

export const adminPending = () => apiGet('/api/admin/pending')
export const adminApprove = (entry_id, approver_id) => apiPost(`/api/admin/approve/${entry_id}`, { approver_id })
export const adminReject = (entry_id) => apiPost(`/api/admin/reject/${entry_id}`)
export const adminEscalations = () => apiGet('/api/admin/escalations')
export const adminResolveEscalation = (id, resolution, admin_id) => apiPost(`/api/admin/escalations/${id}/resolve`, { resolution, admin_id })
export const adminDirectory = () => apiGet('/api/admin/directory')

export function uploadFile(file, { interview_id, entry_id } = {}) {
  const fd = new FormData()
  fd.append('file', file)
  if (interview_id != null) fd.append('interview_id', String(interview_id))
  if (entry_id != null) fd.append('entry_id', String(entry_id))
  return apiUpload('/api/files/upload', fd)
}
