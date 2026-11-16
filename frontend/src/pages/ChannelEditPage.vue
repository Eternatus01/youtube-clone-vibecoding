<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Camera, ImageIcon, Loader2 } from 'lucide-vue-next'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'

type ChannelOut = components['schemas']['ChannelOut']

const USERNAME_MAX = 32

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const username = ref('')
const avatarUrl = ref<string | null>(null)
const coverUrl = ref<string | null>(null)
const channel = ref<ChannelOut | null>(null)
const loading = ref(true)
const error = ref('')
const saving = ref(false)
const uploading = ref<'avatar' | 'cover' | null>(null)

const usernameInput = ref<HTMLInputElement | null>(null)
const avatarInput = ref<HTMLInputElement | null>(null)
const coverInput = ref<HTMLInputElement | null>(null)

// Cache-busting version so a freshly uploaded image is not served stale.
const avatarVersion = ref(0)
const coverVersion = ref(0)

const initial = computed(() => (username.value || '?').charAt(0).toUpperCase())
const usernameChanged = computed(
  () => !!channel.value && username.value !== channel.value.username,
)

const dirty = computed(() => usernameChanged.value)

function withVersion(url: string | null | undefined, version: number): string | null {
  if (!url) return null
  if (!version) return url
  const sep = url.includes('?') ? '&' : '?'
  return `${url}${sep}v=${version}`
}

const avatarSrc = computed(() => withVersion(avatarUrl.value, avatarVersion.value))
const coverSrc = computed(() => withVersion(coverUrl.value, coverVersion.value))

async function load() {
  loading.value = true
  error.value = ''
  const { data, error: apiError } = await api.GET('/api/channels/me')
  if (apiError || !data) {
    error.value = 'Не удалось загрузить канал.'
    loading.value = false
    return
  }
  channel.value = data
  username.value = data.username
  avatarUrl.value = data.avatar_url ?? null
  coverUrl.value = data.cover_url ?? null
  loading.value = false
}

function pickAvatar() {
  avatarInput.value?.click()
}

function pickCover() {
  coverInput.value?.click()
}

function onAvatarChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  input.value = ''
  if (file) void uploadImage('avatar', file)
}

function onCoverChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  input.value = ''
  if (file) void uploadImage('cover', file)
}

function isImage(file: File): boolean {
  return file.type.startsWith('image/')
}

async function uploadImage(kind: 'avatar' | 'cover', file: File) {
  if (!isImage(file)) {
    toast.push('Выберите файл изображения.')
    return
  }
  uploading.value = kind
  try {
    const body = new FormData()
    body.append(kind, file)
    const res = await fetch(`/api/channels/me/${kind}`, {
      method: 'POST',
      credentials: 'include',
      body,
    })
    if (!res.ok) {
      let detail = `Не удалось загрузить ${kind === 'avatar' ? 'аватар' : 'обложку'}`
      try {
        const payload = (await res.json()) as { detail?: unknown }
        if (typeof payload?.detail === 'string') detail = payload.detail
      } catch {
        // Non-JSON error body: keep the generic message.
      }
      throw new Error(detail)
    }
    const data = (await res.json()) as ChannelOut
    channel.value = data
    username.value = data.username
    if (kind === 'avatar') {
      avatarUrl.value = data.avatar_url ?? null
      avatarVersion.value += 1
    } else {
      coverUrl.value = data.cover_url ?? null
      coverVersion.value += 1
    }
    toast.push(kind === 'avatar' ? 'Аватар обновлён' : 'Обложка обновлена')
  } catch (e) {
    toast.push(e instanceof Error ? e.message : 'Ошибка загрузки файла')
  } finally {
    uploading.value = null
  }
}

async function save() {
  if (saving.value) return
  const name = username.value.trim()
  if (!name) {
    toast.push('Имя канала не может быть пустым')
    usernameInput.value?.focus()
    return
  }
  saving.value = true
  const { data, error: apiError } = await api.PATCH('/api/channels/me', {
    body: { username: name },
  })
  saving.value = false
  if (apiError || !data) {
    toast.push(extractError(apiError, 'Не удалось сохранить канал'))
    return
  }
  channel.value = data
  username.value = data.username
  avatarUrl.value = data.avatar_url ?? null
  coverUrl.value = data.cover_url ?? null
  await auth.fetchMe()
  toast.push('Канал сохранён')
  router.push({ name: 'channel', params: { id: data.id } })
}

onMounted(load)
onBeforeUnmount(() => {
  uploading.value = null
})
</script>

<template>
  <div class="page channel-edit">
    <h1 class="page-title">Редактировать канал</h1>

    <div v-if="error" class="error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="load">Повторить</button>
    </div>

    <div v-if="loading" class="edit-panel">
      <div class="skeleton cover-skeleton"></div>
      <div class="skeleton avatar-skeleton"></div>
      <div class="skeleton line-skeleton"></div>
      <div class="skeleton line-skeleton short"></div>
    </div>

    <div v-else class="edit-panel">
      <!-- Cover -->
      <div class="cover-block">
        <div class="cover-preview" :class="{ 'with-cover': !!coverSrc }">
          <img v-if="coverSrc" :src="coverSrc" alt="Обложка канала" class="cover-img" />
        </div>
        <button
          type="button"
          class="pill upload-btn"
          :disabled="uploading !== null"
          @click="pickCover"
        >
          <Loader2 v-if="uploading === 'cover'" :size="16" class="spin" />
          <ImageIcon v-else :size="16" />
          {{ uploading === 'cover' ? 'Загрузка…' : 'Загрузить обложку' }}
        </button>
        <input
          ref="coverInput"
          type="file"
          accept="image/*"
          class="sr-only"
          @change="onCoverChange"
        />
      </div>

      <!-- Avatar -->
      <div class="avatar-block">
        <button
          type="button"
          class="avatar-edit"
          :disabled="uploading !== null"
          :aria-label="'Загрузить аватар'"
          @click="pickAvatar"
        >
          <img v-if="avatarSrc" :src="avatarSrc" alt="Аватар канала" class="avatar-img" />
          <span v-else class="avatar-letter">{{ initial }}</span>
          <span class="avatar-overlay">
            <Loader2 v-if="uploading === 'avatar'" :size="20" class="spin" />
            <Camera v-else :size="20" />
          </span>
        </button>
        <input
          ref="avatarInput"
          type="file"
          accept="image/*"
          class="sr-only"
          @change="onAvatarChange"
        />
      </div>

      <!-- Name -->
      <form class="name-form" @submit.prevent="save">
        <div class="field">
          <label for="channel-username">Название канала</label>
          <input
            id="channel-username"
            ref="usernameInput"
            v-model="username"
            class="input input-lg"
            type="text"
            :maxlength="USERNAME_MAX"
            required
          />
        </div>

        <div class="form-actions">
          <button type="submit" class="btn btn-primary" :disabled="saving || !dirty">
            {{ saving ? 'Сохранение…' : 'Сохранить' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.channel-edit {
  max-width: 860px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 20px;
}

.edit-panel {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 24px;
}

/* ---- Cover ---- */
.cover-block {
  margin-bottom: 20px;
}

.cover-preview {
  width: 100%;
  aspect-ratio: 16 / 5;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--surface-hover) 0%, var(--surface) 100%);
  overflow: hidden;
  position: relative;
  margin-bottom: 12px;
}

.cover-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* ---- Avatar ---- */
.avatar-block {
  margin-bottom: 20px;
}

.avatar-edit {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--surface-hover);
  border: none;
  padding: 0;
  cursor: pointer;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.avatar-letter {
  font-size: 36px;
  font-weight: 500;
  color: var(--text);
  user-select: none;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.avatar-edit:hover .avatar-overlay,
.avatar-edit:focus-visible .avatar-overlay {
  opacity: 1;
}

/* ---- Name form ---- */
.name-form .field {
  margin-bottom: 16px;
}

.field label {
  display: block;
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 6px;
}

.input-lg {
  height: 48px;
  padding: 10px 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

/* ---- Upload pill ---- */
.upload-btn {
  text-decoration: none;
}

.upload-btn:hover {
  background: var(--surface-hover);
}

.upload-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

/* ---- Skeletons ---- */
.cover-skeleton {
  aspect-ratio: 16 / 5;
  border-radius: 12px;
  margin-bottom: 20px;
}

.avatar-skeleton {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  margin-bottom: 20px;
}

.line-skeleton {
  height: 14px;
  margin-bottom: 12px;
}

.line-skeleton.short {
  width: 40%;
}

/* animate-spin */
.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
