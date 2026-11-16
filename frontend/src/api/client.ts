import createClient from 'openapi-fetch'
import type { Middleware } from 'openapi-fetch'
import type { paths } from './schema'

/**
 * Cookie-auth client. No tokens are stored client-side: the browser sends
 * auth cookies automatically (credentials: 'include'). On a 401 from any
 * non-auth endpoint the middleware tries one refresh, replays the request,
 * and notifies the auth store if the session is truly lost.
 */
export const api = createClient<paths>({ baseUrl: '', credentials: 'include' })

type AuthLostHandler = () => void

let authLostHandler: AuthLostHandler | null = null
let refreshInFlight: Promise<boolean> | null = null

export function onAuthLost(handler: AuthLostHandler) {
  authLostHandler = handler
}

async function tryRefresh(): Promise<boolean> {
  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      // Refresh token arrives via HttpOnly cookie; body field is a schema formality.
      body: JSON.stringify({ refresh_token: '' }),
    })
    return res.ok
  } catch {
    return false
  }
}

const authMiddleware: Middleware = {
  async onResponse({ request, response }) {
    if (response.status !== 401) return response
    const path = new URL(request.url).pathname
    if (path.startsWith('/api/auth/')) return response

    refreshInFlight ||= tryRefresh()
    const ok = await refreshInFlight
    refreshInFlight = null

    if (!ok) {
      authLostHandler?.()
      return response
    }
    // Replay the original request with refreshed cookies.
    return fetch(request, { credentials: 'include' })
  },
}

api.use(authMiddleware)

/** Pull a human-readable message out of an openapi-fetch error (FastAPI shape). */
export function extractError(error: unknown, fallback = 'Request failed'): string {
  if (error && typeof error === 'object') {
    const detail = (error as { detail?: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const parts = detail.map((d) =>
        d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : String(d),
      )
      return parts.join('; ') || fallback
    }
    const message = (error as { message?: unknown }).message
    if (typeof message === 'string') return message
  }
  return fallback
}
