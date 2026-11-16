<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const login = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

function safeNext(): string {
  const next = route.query.next
  if (typeof next === 'string' && next.startsWith('/') && !next.startsWith('//')) {
    return next
  }
  return '/'
}

async function submit() {
  error.value = ''
  if (!login.value.trim() || !password.value) {
    error.value = 'Enter your username/email and password.'
    return
  }
  submitting.value = true
  try {
    await auth.login(login.value.trim(), password.value)
    router.push(safeNext())
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Login failed'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth">
    <form class="auth-card" @submit.prevent="submit">
      <h1>Sign in</h1>
      <p class="subtitle">to continue to YouTube Clone</p>

      <div v-if="error" class="error-banner" role="alert">{{ error }}</div>

      <div class="field">
        <label for="login">Username or email</label>
        <input
          id="login"
          v-model="login"
          class="input"
          type="text"
          autocomplete="username"
          required
        />
      </div>

      <div class="field">
        <label for="password">Password</label>
        <input
          id="password"
          v-model="password"
          class="input"
          type="password"
          autocomplete="current-password"
          required
        />
      </div>

      <button class="btn btn-primary submit" type="submit" :disabled="submitting">
        {{ submitting ? 'Signing in…' : 'Sign in' }}
      </button>

      <p class="switch">
        No account?
        <RouterLink :to="{ name: 'register', query: route.query }" class="link">
          Create one
        </RouterLink>
      </p>
    </form>
  </div>
</template>

<style scoped>
.auth {
  display: flex;
  justify-content: center;
  padding: 64px 24px;
}

.auth-card {
  width: 100%;
  max-width: 380px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 32px;
  height: fit-content;
}

h1 {
  font-size: 22px;
  margin-bottom: 4px;
}

.subtitle {
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.submit {
  width: 100%;
  justify-content: center;
  border-radius: 8px;
  margin-top: 8px;
}

.switch {
  margin-top: 20px;
  text-align: center;
  color: var(--text-secondary);
}

.link {
  color: var(--accent);
}

.link:hover {
  text-decoration: underline;
}
</style>
