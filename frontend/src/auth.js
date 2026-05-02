// Single-window auth: one logged-in profile in localStorage, no role-from-path.
import { useEffect, useState } from 'react'

const KEY = 'thoth.user'

export function currentUser() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export function setUser(profile) {
  if (profile) localStorage.setItem(KEY, JSON.stringify(profile))
  else localStorage.removeItem(KEY)
  // Notify same-tab listeners. (`storage` only fires across tabs.)
  window.dispatchEvent(new Event('thoth-user-changed'))
}

export function clearUser() { setUser(null) }

// Hook: re-renders when the logged-in user changes (login / logout / switch).
export function useAuth() {
  const [user, setLocal] = useState(currentUser())
  useEffect(() => {
    const sync = () => setLocal(currentUser())
    window.addEventListener('thoth-user-changed', sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener('thoth-user-changed', sync)
      window.removeEventListener('storage', sync)
    }
  }, [])
  return user
}
