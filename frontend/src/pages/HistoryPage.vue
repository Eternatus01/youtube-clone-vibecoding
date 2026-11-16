<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { History as HistoryIcon, X } from 'lucide-vue-next'
import { api } from '../api/client'
import type { components } from '../api/schema'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { timeAgo } from '../utils/format'
import { useToast } from '../composables/useToast'

type VideoOut = components['schemas']['VideoOut']

/** History list item: backend WatchHistoryOut (items is untyped in the schema). */
type HistoryItem = {
  id: string
  video_id: string
  progress_seconds: number | null
  last_watched_at: string
  video: VideoOut | null
}

const toast = useToast()

const items = ref<HistoryItem[]>([])
const loading = ref(true)
const error = ref('')
const page = ref(1)
const pages = ref(1)
const loadingMore = ref(false)
const clearing = ref(false)

/** Confirm dialog state: null = closed; 'clear' = clear all; item = remove that item. */
const confirmTarget = ref<HistoryItem | 'clear' | null>(null)
const confirmOpen = computed(() => confirmTarget.value !== null)
const confirmTitle = computed(() =>
  confirmTarget.value === 'clear' ? 'Очистить историю' : 'Удалить из истории',
)
const confirmMessage = computed(() => {
  if (confirmTarget.value === 'clear') {
    return 'Очистить всю историю просмотров? Действие нельзя отменить.'
  }
  if (confirmTarget.value === null) return ''
  return `Удалить «${confirmTarget.value.video?.title ?? 'видео'}» из истории просмотров?`
})

const posterFailed = ref<Record<string, boolean>>({})

const visibleItems = computed(() =>
  items.value.filter((item): item is HistoryItem & { video: VideoOut } => item.video !== null),
)
const hasMore = computed(() => page.value < pages.value)

async function load() {
  loading.value = true
  error.value = ''
  const { data, error: apiError } = await api.GET('/api/history/', {
    params: { query: { page: 1, page_size: 20 } },
  })
  if (apiError || !data) {
    error.value = 'Не удалось загрузить историю. Попробуйте ещё раз.'
    items.value = []
  } else {
    items.value = (data.items as HistoryItem[]) ?? []
    page.value = data.page
    pages.value = data.pages
  }
  loading.value = false
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  const { data } = await api.GET('/api/history/', {
    params: { query: { page: page.value + 1, page_size: 20 } },
  })
  if (data) {
    items.value.push(...((data.items as HistoryItem[]) ?? []))
    page.value = data.page
    pages.value = data.pages
  }
  loadingMore.value = false
}

async function removeItem(item: HistoryItem) {
  const { error: apiError } = await api.DELETE('/api/history/{video_id}', {
    params: { path: { video_id: item.video_id } },
  })
  if (!apiError) {
    items.value = items.value.filter((i) => i.video_id !== item.video_id)
    toast.push('Видео удалено из истории')
  } else {
    toast.push('Не удалось удалить из истории. Попробуйте ещё раз.')
  }
}

async function clearAll() {
  if (clearing.value) return
  clearing.value = true
  const { error: apiError } = await api.DELETE('/api/history/')
  if (!apiError) {
    items.value = []
    page.value = 1
    pages.value = 1
    toast.push('История просмотров очищена')
  } else {
    toast.push('Не удалось очистить историю. Попробуйте ещё раз.')
  }
  clearing.value = false
}

function onConfirm() {
  const target = confirmTarget.value
  confirmTarget.value = null
  if (target === 'clear') {
    void clearAll()
  } else if (target) {
    void removeItem(target)
  }
}

function progressPercent(item: HistoryItem): number | null {
  const progress = item.progress_seconds
  const duration = item.video?.duration_seconds
  if (!progress || progress <= 0 || !duration) return null
  return Math.min(100, Math.round((progress / duration) * 100))
}

function onPosterError(videoId: string) {
  posterFailed.value[videoId] = true
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="history-header">
      <h1 class="page-title">История просмотров</h1>
      <button
        v-if="!loading && !error && items.length"
        class="btn clear-btn"
        :disabled="clearing"
        @click="confirmTarget = 'clear'"
      >
        {{ clearing ? 'Очистка…' : 'Очистить историю' }}
      </button>
    </div>

    <div v-if="error" class="error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="load">Повторить</button>
    </div>

    <div v-if="loading" class="history-list" aria-hidden="true">
      <div v-for="i in 6" :key="i" class="history-row">
        <div class="skeleton thumb-skeleton"></div>
        <div class="skeleton-lines">
          <div class="skeleton line"></div>
          <div class="skeleton line short"></div>
        </div>
      </div>
    </div>

    <template v-else-if="!error">
      <div v-if="visibleItems.length" class="history-list">
        <div v-for="item in visibleItems" :key="item.id" class="history-row">
          <RouterLink
            class="thumb-wrap"
            :to="{ name: 'watch', params: { id: item.video.id } }"
            :title="item.video.title"
          >
            <img
              v-if="!posterFailed[item.video.id]"
              class="thumb"
              :src="`/api/videos/${item.video.id}/poster`"
              :alt="item.video.title"
              loading="lazy"
              @error="onPosterError(item.video.id)"
            />
            <span v-else class="thumb thumb-fallback">{{ item.video.title.slice(0, 1).toUpperCase() }}</span>
            <div v-if="progressPercent(item) !== null" class="row-progress-track">
              <div
                class="row-progress-fill"
                :style="{ width: `${progressPercent(item)}%` }"
              ></div>
            </div>
          </RouterLink>
          <div class="row-text">
            <RouterLink
              class="row-title"
              :to="{ name: 'watch', params: { id: item.video.id } }"
            >
              {{ item.video.title }}
            </RouterLink>
            <RouterLink
              v-if="item.video.owner"
              class="row-channel"
              :to="{ name: 'channel', params: { id: item.video.owner_id } }"
            >
              {{ item.video.owner.username || 'Неизвестный канал' }}
            </RouterLink>
            <span v-if="item.last_watched_at" class="row-meta">
              Просмотрено {{ timeAgo(item.last_watched_at) }}
            </span>
          </div>
          <button
            type="button"
            class="icon-btn row-remove"
            title="Удалить из истории"
            aria-label="Удалить из истории"
            @click="confirmTarget = item"
          >
            <X :size="20" stroke-width="1.75" />
          </button>
        </div>
      </div>

      <div v-else class="empty-state">
        <HistoryIcon :size="48" stroke-width="1.75" class="empty-icon" />
        <p>История пуста</p>
        <RouterLink class="btn action-btn" :to="{ name: 'home' }">На главную</RouterLink>
      </div>

      <div v-if="hasMore" class="load-more">
        <button class="btn" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? 'Загрузка…' : 'Загрузить ещё' }}
        </button>
      </div>
    </template>

    <ConfirmDialog
      :open="confirmOpen"
      :title="confirmTitle"
      :message="confirmMessage"
      confirm-text="Удалить"
      cancel-text="Отмена"
      @confirm="onConfirm"
      @cancel="confirmTarget = null"
    />
  </div>
</template>

<style scoped>
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
}

.clear-btn {
  color: var(--danger);
  border: 1px solid var(--divider);
  border-radius: 18px;
  height: 40px;
}

.clear-btn:hover {
  border-color: var(--danger);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.history-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.thumb-wrap {
  position: relative;
  flex-shrink: 0;
  width: 168px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
}

.thumb {
  display: block;
  width: 168px;
  height: 94px;
  object-fit: cover;
}

.thumb-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-2);
  background: var(--surface);
}

.row-progress-track {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 4px;
  background: rgba(0, 0, 0, 0.4);
}

.row-progress-fill {
  height: 100%;
  background: var(--accent);
}

.row-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.row-title {
  color: var(--text);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 4px;
}

.row-channel {
  color: var(--text-2);
  font-size: 12px;
  margin-bottom: 2px;
  width: fit-content;
}

.row-channel:hover {
  color: var(--text);
}

.row-meta {
  color: var(--text-2);
  font-size: 12px;
}

.row-remove {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
}

@media (hover: hover) {
  .row-remove {
    opacity: 0;
    transition: opacity 0.15s ease;
  }

  .history-row:hover .row-remove {
    opacity: 1;
  }
}

@media (hover: none) {
  .row-remove {
    opacity: 1;
  }
}

/* Skeletons */
.thumb-skeleton {
  width: 168px;
  height: 94px;
  border-radius: 8px;
  flex-shrink: 0;
}

.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 4px;
  flex: 1;
}

.line {
  height: 14px;
  width: 70%;
}

.line.short {
  width: 40%;
}

/* Empty state */
.empty-icon {
  color: var(--text-2);
  margin-bottom: 12px;
}

.empty-state p {
  margin-bottom: 16px;
}

.action-btn {
  display: inline-flex;
  border-radius: 18px;
  height: 40px;
}

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>
