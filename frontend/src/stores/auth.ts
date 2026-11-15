import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ id: string; username: string; role: string } | null>(null)
  const isAuthenticated = ref(false)

  function setUser(u: typeof user.value) {
    user.value = u
    isAuthenticated.value = !!u
  }

  function logout() {
    user.value = null
    isAuthenticated.value = false
  }

  return { user, isAuthenticated, setUser, logout }
})
