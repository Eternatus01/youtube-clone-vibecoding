<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const email = ref('')
const password = ref('')
const confirm = ref('')
const error = ref('')
const submitting = ref(false)

const passwordsMatch = computed(() => password.value === confirm.value)

async function submit() {
  error.value = ''
  if (!username.value.trim() || !email.value.trim() || !password.value) {
    error.value = 'Fill in all fields.'
    return
  }
  if (!passwordsMatch.value) {
    error.value = 'Passwords do not match.'
    return
  }
  submitting.value = true
  try {
    await auth.register(username.value.trim(), email.value.trim(), password.value)
    router.push('/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Registration failed'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth">
    <form class="auth-card" @submit.prevent="submit">
      <h1>Create account</h1>
      <p class="subtitle">to upload and watch videos</p>

      <div v-if="error" class="error-banner" role="alert">{{ error }}</div>

      <div class="field">
        <label for="username">Username</label>
        <input
          id="username"
          v-model="username"
          class="input"
          type="text"
          autocomplete="username"
          minlength="3"
          maxlength="50"
          required
        />
      </div>

      <div class="field">
        <label for="email">Email</label>
        <input id="email" v-model="email" class="input" type="email" autocomplete="email" required />
      </div>

      <div class="field">
        <label for="password">Password</label>
        <input
          id="password"
          v-model="password"
          class="input"
          type="password"
          autocomplete="new-password"
          minlength="6"
          required
        />
      </div>

      <div class="field">
        <label for="confirm">Confirm password</label>
        <input
          id="confirm"
          v-model="confirm"
          class="input"
          type="password"
          autocomplete="new-password"
          required
        />
        <span v-if="confirm && !passwordsMatch" class="hint-error">Passwords do not match</span>
      </div>

      <button
        class="btn btn-primary submit"
        type="submit"
        :disabled="submitting || (confirm !== '' && !passwordsMatch)"
      >
        {{ submitting ? 'Creating account…' : 'Create account' }}
      </button>

      <p class="switch">
        Already have an account?
        <RouterLink :to="{ name: 'login', query: route.query }" class="link">Sign in</RouterLink>
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

.hint-error {
  color: var(--danger);
  font-size: 12px;
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
