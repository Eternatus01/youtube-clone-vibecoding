<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'
import { formatViews } from '../utils/format'
import { formatDuration } from '../utils/format'

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
}

const videos = ref<VideoRow[]>([])
const posterFailed = ref<Record<string, boolean>>({})
const loading = ref(true)
const error = ref('')
const message = ref('')

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
  }
}

async function load() {
  loading.value = true
  error.value = ''
  const { data, error: err } = await api.GET('/api/videos/mine', {
    params: { query: { page: page.value, page_size: 20 } },
  })
  if (err || !data) {
    error.value = extractError(err, 'Failed to load your videos')
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
  message.value = ''
  error.value = ''
  loadShares(v)
}

// ---- Shares (owner-only, private videos) ----

async function loadShares(v: VideoRow) {
  v.sharesLoading = true
  const { data, error: err } = await api.GET('/api/videos/{video_id}/shares', {
    params: { path: { video_id: v.id } },
  })
  v.sharesLoading = false
  if (err || !data) {
    v.shareError = extractError(err, 'Failed to load shares')
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
    v.shareError = extractError(err, 'Failed to add share')
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
    v.shareError = extractError(err, 'Failed to remove share')
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
    error.value = extractError(err, 'Failed to update video')
    return
  }
  v.title = v.editTitle.trim() || v.title
  v.description = v.editDescription
  v.visibility = v.editVisibility
  v.editing = false
  message.value = 'Video updated'
  error.value = ''
}

async function removeVideo(v: VideoRow) {
  if (!confirm(`Delete "${v.title}"? This cannot be undone.`)) return
  v.deleting = true
  const { error: err } = await api.DELETE('/api/videos/{video_id}', {
    params: { path: { video_id: v.id } },
  })
  v.deleting = false
  if (err) {
    error.value = extractError(err, 'Failed to delete video')
    return
  }
  videos.value = videos.value.filter((row) => row.id !== v.id)
  total.value = Math.max(0, total.value - 1)
  message.value = 'Video deleted'
}

const visibilityLabel: Record<Visibility, string> = {
  public: 'Public',
  unlisted: 'Unlisted',
  private: 'Private',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1 class="page-title">Your videos</h1>

    <div v-if="error" class="banner error-banner">{{ error }}</div>
    <div v-if="message" class="banner ok-banner">{{ message }}</div>

    <div v-if="loading" class="skeletons">
      <div v-for="n in 3" :key="n" class="video-skeleton card">
        <div class="line-skeleton thumb-skeleton"></div>
        <div class="line-skeleton w60"></div>
        <div class="line-skeleton w40"></div>
      </div>
    </div>

    <div v-else-if="videos.length === 0" class="empty card">
      <p class="empty-title">No videos yet.</p>
      <p class="empty-hint">Videos you upload will appear here.</p>
      <RouterLink to="/upload" class="btn primary-btn">Upload a video</RouterLink>
    </div>

    <div v-else class="video-list">
      <div v-for="v in videos" :key="v.id" class="video-row card">
        <RouterLink :to="{ name: 'watch', params: { id: v.id } }" class="thumb-wrap">
          <img
            v-if="!posterFailed[v.id]"
            :src="`/api/videos/${v.id}/poster`"
            :alt="v.title"
            class="thumb"
            loading="lazy"
            @error="posterFailed[v.id] = true"
          />
          <div v-else class="thumb thumb-placeholder">▶</div>
          <span class="duration">{{ formatDuration(v.duration_seconds) }}</span>
        </RouterLink>

        <div class="row-body">
          <template v-if="!v.editing">
            <div class="row-head">
              <RouterLink
                :to="{ name: 'watch', params: { id: v.id } }"
                class="row-title"
              >{{ v.title }}</RouterLink>
              <span class="visibility-badge">
                {{ visibilityLabel[v.visibility as Visibility] ?? v.visibility }}
              </span>
            </div>
            <p class="row-desc">{{ v.description || 'No description' }}</p>
            <p class="row-meta">
              {{ formatViews(v.views) }} · {{ formatDate(v.created_at) }}
              <span v-if="v.status && v.status !== 'ready'"> · {{ v.status }}</span>
            </p>
            <div class="row-actions">
              <button class="btn" @click="startEdit(v)">Edit</button>
              <button class="btn danger-btn" :disabled="v.deleting" @click="removeVideo(v)">
                {{ v.deleting ? 'Deleting…' : 'Delete' }}
              </button>
            </div>
          </template>

          <template v-else>
            <form class="edit-form" @submit.prevent="saveEdit(v)">
              <label class="field">
                <span class="field-label">Title</span>
                <input v-model="v.editTitle" type="text" maxlength="150" />
              </label>
              <label class="field">
                <span class="field-label">Description</span>
                <textarea v-model="v.editDescription" rows="3"></textarea>
              </label>
              <label class="field">
                <span class="field-label">Visibility</span>
                <select v-model="v.editVisibility">
                  <option value="public">Public</option>
                  <option value="unlisted">Unlisted</option>
                  <option value="private">Private</option>
                </select>
              </label>
              <div class="edit-actions">
                <button class="btn primary-btn" type="submit" :disabled="v.saving">
                  {{ v.saving ? 'Saving…' : 'Save' }}
                </button>
                <button class="btn" type="button" @click="cancelEdit(v)">Cancel</button>
              </div>

              <div class="shares-section">
                <h3 class="shares-title">Shares</h3>
                <p class="shares-hint">
                  People who can watch this video when it is private or unlisted.
                </p>
                <div v-if="v.sharesLoading" class="shares-loading">Loading shares…</div>
                <p v-else-if="v.shares.length === 0" class="shares-empty">
                  Not shared with anyone yet.
                </p>
                <ul v-else class="shares-list">
                  <li v-for="s in v.shares" :key="s.id" class="share-item">
                    <span class="share-user">{{ s.user?.username ?? s.user_id }}</span>
                    <button
                      class="btn danger-btn"
                      :disabled="v.shareBusy"
                      @click="removeShare(v, s)"
                    >Remove</button>
                  </li>
                </ul>
                <p v-if="v.shareError" class="share-error">{{ v.shareError }}</p>
                <form class="share-add" @submit.prevent="addShare(v)">
                  <input
                    v-model="v.shareUsername"
                    type="text"
                    placeholder="Username to share with"
                  />
                  <button class="btn" type="submit" :disabled="v.shareBusy || !v.shareUsername.trim()">
                    Add
                  </button>
                </form>
              </div>
            </form>
          </template>
        </div>
      </div>
    </div>

    <div v-if="pages > 1" class="pager">
      <button class="btn" :disabled="page <= 1" @click="goTo(page - 1)">Previous</button>
      <span class="pager-info">Page {{ page }} of {{ pages }}</span>
      <button class="btn" :disabled="page >= pages" @click="goTo(page + 1)">Next</button>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

.page-title {
  font-size: 22px;
  margin: 0 0 16px;
}

.banner {
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
}

.error-banner {
  background: color-mix(in srgb, var(--danger) 12%, transparent);
  color: var(--danger);
  border: 1px solid var(--danger);
}

.ok-banner {
  background: color-mix(in srgb, #2e7d32 12%, transparent);
  border: 1px solid #2e7d32;
}

.skeletons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 12px;
}

.video-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.line-skeleton {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(
    90deg,
    var(--skeleton) 25%,
    var(--skeleton-shine) 50%,
    var(--skeleton) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

.thumb-skeleton {
  height: 90px;
  border-radius: 8px;
}

.w60 { width: 60%; }
.w40 { width: 40%; }

@keyframes shimmer {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}

.empty {
  padding: 40px 16px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-title {
  color: var(--text);
  font-size: 16px;
  margin: 0 0 4px;
}

.empty-hint {
  margin: 0 0 16px;
}

.video-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.video-row {
  display: flex;
  gap: 14px;
  padding: 12px;
}

.thumb-wrap {
  position: relative;
  flex: 0 0 160px;
}

.thumb {
  width: 160px;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: 8px;
  background: var(--skeleton);
}

.thumb-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.duration {
  position: absolute;
  right: 4px;
  bottom: 4px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 11px;
  padding: 1px 4px;
  border-radius: 4px;
}

.row-body {
  flex: 1;
  min-width: 0;
}

.row-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.row-title {
  color: var(--text);
  font-weight: 600;
  text-decoration: none;
  font-size: 15px;
}

.row-title:hover {
  text-decoration: underline;
}

.visibility-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.row-desc {
  margin: 4px 0;
  color: var(--text-secondary);
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.row-meta {
  margin: 0 0 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.row-actions {
  display: flex;
  gap: 8px;
}

.edit-form .field {
  display: flex;
  flex-direction: column;
  margin-bottom: 10px;
}

.field-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.edit-form input,
.edit-form textarea,
.edit-form select {
  background: var(--input-bg);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
}

.edit-actions {
  display: flex;
  gap: 8px;
}

.shares-section {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.shares-title {
  font-size: 14px;
  margin: 0 0 4px;
}

.shares-hint,
.shares-empty,
.shares-loading {
  color: var(--text-secondary);
  font-size: 12px;
  margin: 0 0 8px;
}

.shares-list {
  list-style: none;
  margin: 0 0 8px;
  padding: 0;
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
  margin: 0 0 8px;
}

.share-add {
  display: flex;
  gap: 8px;
}

.share-add input {
  flex: 1;
  background: var(--input-bg);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 6px 10px;
  font: inherit;
  font-size: 13px;
}

.btn {
  background: var(--bg-elevated);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 6px 14px;
  border-radius: 18px;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.btn:hover:not(:disabled) {
  background: var(--bg-hover);
}

.primary-btn {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.primary-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.danger-btn {
  color: var(--danger);
}

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.pager-info {
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
