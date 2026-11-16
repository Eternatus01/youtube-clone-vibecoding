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
    error.value = 'Заполните все поля.'
    return
  }
  if (!passwordsMatch.value) {
    error.value = 'Пароли не совпадают.'
    return
  }
  submitting.value = true
  try {
    await auth.register(username.value.trim(), email.value.trim(), password.value)
    router.push('/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось зарегистрироваться'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth">
    <div class="auth-wrap">
      <div class="logo" aria-label="YouTube">
        <span class="logo-mark">
          <svg viewBox="0 0 68 48" width="40" height="28">
            <path
              class="logo-play"
              d="M66.52 7.74c-.78-2.93-2.49-5.41-5.42-6.19C55.79.13 34 0 34 0S12.21.13 6.9 1.55c-2.93.78-4.63 3.26-5.42 6.19C.06 13.05 0 24 0 24s.06 10.95 1.48 16.26c.78 2.93 2.49 5.41 5.42 6.19C12.21 47.87 34 48 34 48s21.79-.13 27.1-1.55c2.93-.78 4.64-3.26 5.42-6.19C67.94 34.95 68 24 68 24s-.06-10.95-1.48-16.26z"
              fill="#ff0000"
            />
            <path d="M45 24 27 14v20" fill="#fff" />
          </svg>
        </span>
        <span class="logo-word">YouTube</span>
      </div>

      <form class="auth-card" @submit.prevent="submit">
        <h1>Регистрация</h1>

        <div class="field">
          <label for="username">Имя пользователя</label>
          <input
            id="username"
            v-model="username"
            class="input input-lg"
            type="text"
            autocomplete="username"
            minlength="3"
            maxlength="50"
            required
          />
        </div>

        <div class="field">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            class="input input-lg"
            type="email"
            autocomplete="email"
            required
          />
        </div>

        <div class="field">
          <label for="password">Пароль</label>
          <input
            id="password"
            v-model="password"
            class="input input-lg"
            type="password"
            autocomplete="new-password"
            minlength="6"
            required
          />
        </div>

        <div class="field">
          <label for="confirm">Подтверждение пароля</label>
          <input
            id="confirm"
            v-model="confirm"
            class="input input-lg"
            type="password"
            autocomplete="new-password"
            required
          />
        </div>

        <p v-if="error" class="inline-error" role="alert">{{ error }}</p>

        <button
          class="btn btn-primary submit"
          type="submit"
          :disabled="submitting || (confirm !== '' && !passwordsMatch)"
        >
          {{ submitting ? 'Регистрация…' : 'Зарегистрироваться' }}
        </button>

        <p class="switch">
          Уже есть аккаунт?
          <RouterLink :to="{ name: 'login', query: route.query }" class="link">Войти</RouterLink>
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.auth {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - var(--topbar-h));
  padding: 24px;
}

.auth-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 6px;
}

.logo-mark {
  display: flex;
}

.logo-word {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: var(--text);
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: var(--surface);
  border-radius: 12px;
  padding: 32px;
  height: fit-content;
}

h1 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 24px;
}

.field label {
  font-size: 12px;
  color: var(--text-2);
}

.input-lg {
  height: 48px;
  padding: 10px 12px;
}

.submit {
  width: 100%;
  justify-content: center;
  height: 40px;
  border-radius: 18px;
  margin-top: 8px;
}

.inline-error {
  color: var(--danger);
  font-size: 12px;
  margin-bottom: 12px;
}

.switch {
  margin-top: 20px;
  text-align: center;
  color: var(--text-2);
  font-size: 14px;
}

.link {
  color: var(--accent);
}

.link:hover {
  text-decoration: underline;
}
</style>
