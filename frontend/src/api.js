import { currentUser } from './auth'

const BASE = ''  // Vite proxy forwards /api to :8000

function profileHeaders() {
  const p = currentUser()
  return p ? { 'X-Profile-Id': String(p.id) } : {}
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

// Profiles
export const listProfiles = (role) => apiGet(`/api/profiles${role ? `?role=${role}` : ''}`)
export const getProfile = (id) => apiGet(`/api/profiles/${id}`)
export const getProfileSubjects = (id) => apiGet(`/api/profiles/${id}/subjects`)
export const createProfile = (payload) => apiPost('/api/profiles', payload)
export const clearReviewRequest = (id) => apiPost(`/api/profiles/${id}/clear-review-request`)

// Subjects
export const listSubjects = () => apiGet('/api/subjects')
export const createSubject = (payload) => apiPost('/api/subjects', payload)

// Query
export const query = (question) => apiPost('/api/query', { question })
export const queryHistory = () => apiGet('/api/query/history')
export function queryWithFile(question, file) {
  const fd = new FormData()
  fd.append('question', question)
  fd.append('file', file)
  return apiUpload('/api/query/with-file', fd)
}

// Interviews
export const startInterview = (sme_id, subject_id, mode = 'structured') =>
  apiPost('/api/interviews/start', { sme_id, subject_id, mode })
export const sendInterviewMessage = (id, content) => apiPost(`/api/interviews/${id}/message`, { content })
export const synthesizeInterview = (id) => apiPost(`/api/interviews/${id}/synthesize`)
export const reviewInterview = (id, action, feedback) => apiPost(`/api/interviews/${id}/review`, { action, feedback })
export const getInterview = (id) => apiGet(`/api/interviews/${id}`)
export const listInterviews = (sme_id) => apiGet(`/api/interviews${sme_id != null ? `?sme_id=${sme_id}` : ''}`)

// SME Review
export const pendingForSme = (sme_id) => apiGet(`/api/review/pending?sme_id=${sme_id}`)
export const reviewEntry = (entry_id, action, reviewer_id, feedback) =>
  apiPost(`/api/review/${entry_id}`, { action, reviewer_id, feedback })

// Admin
export const adminPending = () => apiGet('/api/admin/pending')
export const adminApprove = (entry_id, approver_id) => apiPost(`/api/admin/approve/${entry_id}`, { approver_id })
export const adminReject = (entry_id, reason) => apiPost(`/api/admin/reject/${entry_id}`, { reason })
export const adminEscalations = (status) => apiGet(`/api/admin/escalations${status ? `?status=${status}` : ''}`)
export const adminGetEscalation = (id) => apiGet(`/api/admin/escalations/${id}`)
export const adminResolveEscalation = (id, resolution, admin_id) =>
  apiPost(`/api/admin/escalations/${id}/resolve`, { resolution, admin_id })
export const adminDirectory = () => apiGet('/api/admin/directory')
export const adminRequestReview = (sme_id, admin_id, message) =>
  apiPost('/api/admin/request-review', { sme_id, admin_id, message })

// Files
export function uploadFile(file, { interview_id, entry_id } = {}) {
  const fd = new FormData()
  fd.append('file', file)
  if (interview_id != null) fd.append('interview_id', String(interview_id))
  if (entry_id != null) fd.append('entry_id', String(entry_id))
  return apiUpload('/api/files/upload', fd)
}
