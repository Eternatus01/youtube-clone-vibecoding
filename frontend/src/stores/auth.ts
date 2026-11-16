import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, extractError, onAuthLost } from '../api/client'
import type { components } from '../api/schema'

type UserOut = components['schemas']['UserOut']

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserOut | null>(null)
  const isAuthenticated = computed(() => user.value !== null)
  const ready = ref(false)

  let readyPromise: Promise<void> | null = null

  onAuthLost(() => {
    user.value = null
  })

  async function fetchMe() {
    const { data, error } = await api.GET('/api/auth/me')
    if (error || !data) {
      // 401 already went through one refresh attempt in the client middleware.
      user.value = null
      return
    }
    user.value = data
  }

  /** Restore the session once on startup; guards await this. */
  function init(): Promise<void> {
    readyPromise ||= fetchMe().finally(() => {
      ready.value = true
    })
    return readyPromise
  }

  async function login(login: string, password: string) {
    const { data, error } = await api.POST('/api/auth/login', {
      body: { login, password },
    })
    if (error || !data) throw new Error(extractError(error, 'Login failed'))
    // Tokens stay in cookies; only the user profile is kept in memory.
    user.value = data.user
  }

  async function register(username: string, email: string, password: string) {
    const { data, error } = await api.POST('/api/auth/register', {
      body: { username, email, password },
    })
    if (error || !data) throw new Error(extractError(error, 'Registration failed'))
    user.value = data.user
  }

  async function refresh() {
    const { error } = await api.POST('/api/auth/refresh', {
      body: { refresh_token: '' },
    })
    if (error) {
      user.value = null
      throw new Error(extractError(error, 'Session expired'))
    }
    await fetchMe()
  }

  async function logout() {
    try {
      await api.POST('/api/auth/logout')
    } catch {
      // Clear local state even if the server call fails.
    }
    user.value = null
  }

  return { user, isAuthenticated, ready, init, fetchMe, login, register, refresh, logout }
})
