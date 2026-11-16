<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { components } from '../api/schema'
import VideoCard from '../components/VideoCard.vue'
import { timeAgo } from '../utils/format'

type VideoOut = components['schemas']['VideoOut']

/** History list item: backend WatchHistoryOut (items is untyped in the schema). */
type HistoryItem = {
  id: string
  video_id: string
  progress_seconds: number | null
  last_watched_at: string
  video: VideoOut | null
}

const items = ref<HistoryItem[]>([])
const loading = ref(true)
const error = ref('')
const page = ref(1)
const pages = ref(1)
const loadingMore = ref(false)
const clearing = ref(false)

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
  }
}

async function clearAll() {
  if (clearing.value) return
  if (!window.confirm('Очистить всю историю просмотров?')) return
  clearing.value = true
  const { error: apiError } = await api.DELETE('/api/history/')
  if (!apiError) {
    items.value = []
    page.value = 1
    pages.value = 1
  }
  clearing.value = false
}

function progressPercent(item: HistoryItem): number | null {
  const progress = item.progress_seconds
  const duration = item.video?.duration_seconds
  if (!progress || progress <= 0 || !duration) return null
  return Math.min(100, Math.round((progress / duration) * 100))
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="history-header">
      <h1 class="page-title">История</h1>
      <button
        v-if="!loading && !error && items.length"
        class="btn"
        :disabled="clearing"
        @click="clearAll"
      >
        {{ clearing ? 'Очистка…' : 'Очистить историю' }}
      </button>
    </div>

    <div v-if="error" class="error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="load">Повторить</button>
    </div>

    <div v-if="loading" class="spinner-wrap">
      <span class="spinner" role="status" aria-label="Загрузка"></span>
    </div>

    <template v-else-if="!error">
      <div v-if="visibleItems.length" class="grid">
        <div v-for="item in visibleItems" :key="item.id" class="history-cell">
          <VideoCard :video="item.video" />
          <button
            class="item-remove"
            title="Удалить из истории"
            aria-label="Удалить из истории"
            @click="removeItem(item)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path
                d="M18.3 5.7 12 12l6.3 6.3-1.4 1.4L10.6 13.4 4.3 19.7 2.9 18.3 9.2 12 2.9 5.7 4.3 4.3l6.3 6.3 6.3-6.3 1.4 1.4z"
              />
            </svg>
          </button>
          <div class="history-meta">
            <span v-if="progressPercent(item) !== null" class="progress-label">
              Просмотрено: {{ progressPercent(item) }}%
            </span>
            <span v-if="item.last_watched_at" class="watched-at">
              {{ timeAgo(item.last_watched_at) }}
            </span>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <h2>История просмотров пуста</h2>
        <p>Начните смотреть видео!</p>
      </div>

      <div v-if="hasMore" class="load-more">
        <button class="btn" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? 'Загрузка…' : 'Загрузить ещё' }}
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px 16px;
}

.history-cell {
  position: relative;
}

.item-remove {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, background 0.15s ease;
}

.history-cell:hover .item-remove {
  opacity: 1;
}

.item-remove:hover {
  background: rgba(0, 0, 0, 0.95);
}

.history-meta {
  display: flex;
  gap: 8px;
  align-items: baseline;
  padding: 2px 4px 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.progress-label {
  color: var(--text);
  font-weight: 500;
}

.spinner-wrap {
  display: flex;
  justify-content: center;
  padding: 64px 0;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

@media (hover: none) {
  .item-remove {
    opacity: 1;
  }
}
</style>
