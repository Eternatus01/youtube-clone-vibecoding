<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Pencil, Trash2, Upload, VideoOff } from 'lucide-vue-next'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'
import { useToast } from '../composables/useToast'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { formatDuration, formatViews } from '../utils/format'

type VideoOut = components['schemas']['VideoOut']
type VideoShareOut = components['schemas']['VideoShareOut']
type Visibility = 'public' | 'private' | 'unlisted'

interface VideoRow extends VideoOut {
  // Per-row UI state, never sent to the API.
  editing: boolean
  editTitle: string
  editDescription: string
  editVisibility: Visibility
  saving: boolean
  deleting: boolean
  shares: VideoShareOut[]
  sharesLoading: boolean
  shareUsername: string
  shareError: string
  shareBusy: boolean
  posterVersion: number
  posterBusy: boolean
}

const videos = ref<VideoRow[]>([])
const posterFailed = ref<Record<string, boolean>>({})
const loading = ref(true)
const error = ref('')
const toast = useToast()

// Pending row for the delete confirmation dialog.
const deleteTarget = ref<VideoRow | null>(null)

const page = ref(1)
const pages = ref(1)
const total = ref(0)

function toRow(v: VideoOut): VideoRow {
  return {
    ...v,
    editing: false,
    editTitle: v.title,
    editDescription: v.description ?? '',
    editVisibility: (v.visibility as Visibility) ?? 'public',
    saving: false,
    deleting: false,
    shares: [],
    sharesLoading: false,
    shareUsername: '',
    shareError: '',
    shareBusy: false,
    posterVersion: 0,
    posterBusy: false,
  }
}

async function load() {
  loading.value = true
  error.value = ''
  const { data, error: err } = await api.GET('/api/videos/mine', {
    params: { query: { page: page.value, page_size: 20 } },
  })
  if (err || !data) {
    error.value = extractError(err, 'Не удалось загрузить ваши видео')
    videos.value = []
    loading.value = false
    return
  }
  videos.value = data.items.map((item) => toRow(item as VideoOut))
  total.value = data.total
  page.value = data.page
  pages.value = data.pages
  loading.value = false
}

function goTo(p: number) {
  if (p >= 1 && p <= pages.value && p !== page.value) {
    page.value = p
    load()
  }
}

function startEdit(v: VideoRow) {
  v.editTitle = v.title
  v.editDescription = v.description ?? ''
  v.editVisibility = (v.visibility as Visibility) ?? 'public'
  v.editing = true
  error.value = ''
  loadShares(v)
}

// ---- Poster (custom thumbnail) ----

function posterSrc(v: VideoRow): string {
  return `/api/videos/${v.id}/poster?v=${v.posterVersion}`
}

async function uploadPoster(v: VideoRow, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  input.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    toast.push('Выберите файл изображения.')
    return
  }
  v.posterBusy = true
  try {
    const body = new FormData()
    body.append('poster', file)
    const res = await fetch(`/api/uploads/${v.id}/poster`, {
      method: 'POST',
      credentials: 'include',
      body,
    })
    if (!res.ok) {
      let detail = 'Не удалось загрузить превью'
      try {
        const payload = (await res.json()) as { detail?: unknown }
        if (typeof payload?.detail === 'string') detail = payload.detail
      } catch {
        // ignore non-JSON
      }
      throw new Error(detail)
    }
    v.posterVersion += 1
    posterFailed.value[v.id] = false
    toast.push('Превью обновлено')
  } catch (e) {
    toast.push(e instanceof Error ? e.message : 'Ошибка загрузки превью')
  } finally {
    v.posterBusy = false
  }
}

// ---- Shares (owner-only, private videos) ----

async function loadShares(v: VideoRow) {
  v.sharesLoading = true
  const { data, error: err } = await api.GET('/api/videos/{video_id}/shares', {
    params: { path: { video_id: v.id } },
  })
  v.sharesLoading = false
  if (err || !data) {
    v.shareError = extractError(err, 'Не удалось загрузить список доступа')
    return
  }
  v.shares = data
  v.shareError = ''
}

async function addShare(v: VideoRow) {
  const username = v.shareUsername.trim()
  if (!username) return
  v.shareBusy = true
  const { data, error: err } = await api.POST('/api/videos/{video_id}/shares', {
    params: { path: { video_id: v.id } },
    body: { username },
  })
  v.shareBusy = false
  if (err || !data) {
    v.shareError = extractError(err, 'Не удалось открыть доступ')
    return
  }
  v.shares.push(data)
  v.shareUsername = ''
  v.shareError = ''
}

async function removeShare(v: VideoRow, share: VideoShareOut) {
  v.shareBusy = true
  const { error: err } = await api.DELETE('/api/videos/{video_id}/shares/{user_id}', {
    params: { path: { video_id: v.id, user_id: share.user_id } },
  })
  v.shareBusy = false
  if (err) {
    v.shareError = extractError(err, 'Не удалось закрыть доступ')
    return
  }
  v.shares = v.shares.filter((s) => s.id !== share.id)
}

function cancelEdit(v: VideoRow) {
  v.editing = false
}

async function saveEdit(v: VideoRow) {
  v.saving = true
  const { error: err } = await api.PATCH('/api/videos/{video_id}', {
    params: { path: { video_id: v.id } },
    body: {
      title: v.editTitle.trim() || null,
      description: v.editDescription,
      visibility: v.editVisibility,
    },
  })
  v.saving = false
  if (err) {
    toast.push(extractError(err, 'Не удалось обновить видео'))
    return
  }
  v.title = v.editTitle.trim() || v.title
  v.description = v.editDescription
  v.visibility = v.editVisibility
  v.editing = false
  toast.push('Видео обновлено')
}

// ---- Delete: ConfirmDialog instead of window.confirm ----

function askDelete(v: VideoRow) {
  error.value = ''
  deleteTarget.value = v
}

async function confirmDelete() {
  const v = deleteTarget.value
  deleteTarget.value = null
  if (!v) return
  v.deleting = true
  const { error: err } = await api.DELETE('/api/videos/{video_id}', {
    params: { path: { video_id: v.id } },
  })
  v.deleting = false
  if (err) {
    toast.push(extractError(err, 'Не удалось удалить видео'))
    return
  }
  videos.value = videos.value.filter((row) => row.id !== v.id)
  total.value = Math.max(0, total.value - 1)
  toast.push('Видео удалено')
}

const visibilityLabel: Record<Visibility, string> = {
  public: 'Публичное',
  private: 'Приватное',
  unlisted: 'По ссылке',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1 class="page-title">Мои видео</h1>

    <!-- Error state -->
    <div v-if="error" class="load-error">
      <p>{{ error }}</p>
      <button class="btn" type="button" @click="load">Повторить</button>
    </div>

    <!-- Loading: rows matching real geometry -->
    <div v-if="loading" class="skeletons" aria-hidden="true">
      <div v-for="n in 4" :key="n" class="video-row row-skeleton">
        <div class="thumb-skeleton"></div>
        <div class="row-info">
          <div class="line-skeleton w60"></div>
          <div class="line-skeleton w40"></div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="videos.length === 0" class="empty-state">
      <VideoOff class="lucide-icon" :size="48" />
      <p>У вас пока нет видео</p>
      <RouterLink to="/upload" class="btn btn-accent">Загрузить видео</RouterLink>
    </div>

    <div v-else class="video-list">
      <div v-for="v in videos" :key="v.id" class="video-row">
        <template v-if="!v.editing">
          <RouterLink class="thumb-link" :to="`/watch/${v.id}`">
            <div class="thumb">
              <img
                v-if="!posterFailed[v.id]"
                :src="posterSrc(v)"
                alt=""
                loading="lazy"
                @error="posterFailed[v.id] = true"
              />
              <span
                v-if="v.duration_seconds"
                class="duration"
              >{{ formatDuration(v.duration_seconds) }}</span>
            </div>
          </RouterLink>

          <div class="row-info">
            <RouterLink class="title-link" :to="`/watch/${v.id}`">
              <h3 class="row-title">{{ v.title }}</h3>
            </RouterLink>
            <p class="row-meta">
              <span class="visibility-pill">{{ visibilityLabel[v.visibility as Visibility] ?? v.visibility }}</span>
              <span>{{ formatViews(v.views) }} · {{ formatDate(v.created_at) }}</span>
            </p>
            <div class="row-actions">
              <button class="btn btn-ghost" type="button" @click="startEdit(v)">
                <Pencil class="lucide-icon" :size="16" />
                Редактировать
              </button>
              <button
                class="icon-btn delete-btn"
                type="button"
                title="Удалить"
                :disabled="v.deleting"
                @click="askDelete(v)"
              >
                <Trash2 class="lucide-icon" :size="18" />
              </button>
            </div>
          </div>
        </template>

        <!-- Inline edit form -->
        <form v-else class="edit-form" @submit.prevent="saveEdit(v)">
          <label class="field">
            <span>Название</span>
            <input v-model="v.editTitle" type="text" required />
          </label>
          <label class="field">
            <span>Описание</span>
            <textarea v-model="v.editDescription" rows="3"></textarea>
          </label>
          <label class="field">
            <span>Доступ</span>
            <select v-model="v.editVisibility">
              <option value="public">Публичное</option>
              <option value="private">Приватное</option>
              <option value="unlisted">По ссылке</option>
            </select>
          </label>

          <div class="field">
            <span>Обложка (превью)</span>
            <div class="poster-edit">
              <div class="poster-preview">
                <img
                  v-if="!posterFailed[v.id]"
                  :src="posterSrc(v)"
                  alt=""
                  @error="posterFailed[v.id] = true"
                />
              </div>
              <label class="btn btn-ghost poster-pick" :class="{ busy: v.posterBusy }">
                <Upload class="lucide-icon" :size="16" />
                {{ v.posterBusy ? 'Загрузка…' : 'Выбрать превью' }}
                <input
                  type="file"
                  accept="image/*"
                  hidden
                  :disabled="v.posterBusy"
                  @change="uploadPoster(v, $event)"
                />
              </label>
            </div>
          </div>

          <!-- Shares section -->
          <div class="shares">
            <p class="shares-title">Общий доступ</p>
            <p v-if="v.sharesLoading" class="shares-hint">Загрузка…</p>
            <p v-else-if="v.shares.length === 0" class="shares-hint">
              Видео доступно по ссылке. Добавьте пользователей, чтобы открыть доступ.
            </p>
            <ul v-else class="share-list">
              <li v-for="s in v.shares" :key="s.id" class="share-item">
                <span class="share-user">{{ s.user?.username ?? s.user_id }}</span>
                <button
                  class="btn btn-ghost"
                  type="button"
                  :disabled="v.shareBusy"
                  @click="removeShare(v, s)"
                >Закрыть доступ</button>
              </li>
            </ul>
            <p v-if="v.shareError" class="share-error">{{ v.shareError }}</p>
            <form class="share-add" @submit.prevent="addShare(v)">
              <input
                v-model="v.shareUsername"
                type="text"
                placeholder="Имя пользователя"
              />
              <button class="btn" type="submit" :disabled="v.shareBusy || !v.shareUsername.trim()">
                Добавить
              </button>
            </form>
          </div>

          <div class="edit-actions">
            <button class="btn btn-accent" type="submit" :disabled="v.saving">Сохранить</button>
            <button class="btn" type="button" @click="cancelEdit(v)">Отмена</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="pages > 1" class="pager">
      <button class="btn" :disabled="page <= 1" @click="goTo(page - 1)">Предыдущая</button>
      <span class="pager-info">Страница {{ page }} из {{ pages }}</span>
      <button class="btn" :disabled="page >= pages" @click="goTo(page + 1)">Следующая</button>
    </div>

    <ConfirmDialog
      :open="!!deleteTarget"
      title="Удалить видео"
      :message="deleteTarget
        ? `«${deleteTarget.title}» будет удалён безвозвратно.`
        : 'Видео будет удалено безвозвратно.'"
      confirm-text="Удалить"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 16px;
}

/* ---- Video rows: thumb 168x94 + info ---- */
.video-list {
  display: flex;
  flex-direction: column;
}

.video-row {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--divider);
}

.thumb-link {
  flex-shrink: 0;
}

.thumb {
  position: relative;
  width: 168px;
  height: 94px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.duration {
  position: absolute;
  right: 4px;
  bottom: 4px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}

.row-info {
  min-width: 0;
  flex: 1;
}

.row-title {
  font-size: 14px;
  font-weight: 500;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.title-link {
  color: var(--text);
}

.row-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  color: var(--text-2);
  font-size: 12px;
  margin-top: 4px;
}

/* Visibility: small outlined text pill, no saturated fill. */
.visibility-pill {
  display: inline-block;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  border: 1px solid var(--divider);
  color: var(--text-2);
  white-space: nowrap;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
}

.delete-btn {
  color: var(--text-2);
}

.delete-btn:hover {
  color: var(--danger);
}

/* ---- Inline edit form ---- */
.edit-form {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field span {
  font-size: 12px;
  color: var(--text-2);
}

.field input,
.field textarea,
.field select {
  background: var(--bg);
  border: 1px solid var(--divider);
  color: var(--text);
  border-radius: 8px;
  padding: 8px 12px;
  font: inherit;
  font-size: 14px;
}

.field textarea {
  resize: vertical;
}

.edit-actions {
  display: flex;
  gap: 8px;
}

/* ---- Poster edit ---- */
.poster-edit {
  display: flex;
  align-items: center;
  gap: 12px;
}

.poster-preview {
  width: 160px;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
  flex-shrink: 0;
}

.poster-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.poster-pick {
  cursor: pointer;
  width: fit-content;
}

.poster-pick.busy {
  opacity: 0.6;
  pointer-events: none;
}

/* ---- Shares ---- */
.shares {
  border: 1px solid var(--divider);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shares-title {
  font-size: 13px;
  font-weight: 500;
}

.shares-hint {
  color: var(--text-2);
  font-size: 12px;
}

.share-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.share-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}

.share-user {
  color: var(--text);
}

.share-error {
  color: var(--danger);
  font-size: 12px;
  margin: 0;
}

.share-add {
  display: flex;
  gap: 8px;
}

.share-add input {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--divider);
  color: var(--text);
  border-radius: 8px;
  padding: 6px 10px;
  font: inherit;
  font-size: 13px;
}

/* ---- Empty / error states ---- */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 64px 16px;
  color: var(--text-2);
  text-align: center;
}

.empty-state .btn {
  margin-top: 4px;
}

.load-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 64px 16px;
  color: var(--text-2);
  text-align: center;
}

.load-error p {
  max-width: 480px;
}

/* ---- Skeletons: same geometry as real rows ---- */
.thumb-skeleton {
  width: 168px;
  height: 94px;
  border-radius: 8px;
  flex-shrink: 0;
  background: linear-gradient(
    90deg,
    var(--surface) 25%,
    var(--surface-hover) 50%,
    var(--surface) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

.row-skeleton .row-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 6px;
}

.line-skeleton {
  height: 14px;
  border-radius: 6px;
  background: linear-gradient(
    90deg,
    var(--surface) 25%,
    var(--surface-hover) 50%,
    var(--surface) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

.w60 { width: 60%; }
.w40 { width: 40%; }

@keyframes shimmer {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.pager-info {
  color: var(--text-2);
  font-size: 13px;
}

@media (max-width: 560px) {
  .thumb {
    width: 128px;
    height: 72px;
  }

  .thumb-skeleton {
    width: 128px;
    height: 72px;
  }
}
</style>
