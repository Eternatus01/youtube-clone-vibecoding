<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Search as SearchIcon } from 'lucide-vue-next'
import { api } from '../api/client'
import type { components } from '../api/schema'
import {
  formatDuration,
  formatSubscribers,
  formatViews,
  timeAgo,
} from '../utils/format'

type SearchResult = components['schemas']['SearchResult']

const route = useRoute()

const result = ref<SearchResult | null>(null)
const loading = ref(true)
const error = ref('')

const query = computed(() =>
  typeof route.query.q === 'string' ? route.query.q.trim() : '',
)

async function load() {
  loading.value = true
  error.value = ''
  if (!query.value) {
    result.value = null
    loading.value = false
    return
  }
  const { data, error: apiError } = await api.GET('/api/search/', {
    params: { query: { q: query.value, page: 1, page_size: 40 } },
  })
  if (apiError || !data) {
    error.value = 'Не удалось выполнить поиск. Попробуйте ещё раз.'
    result.value = null
  } else {
    result.value = data
  }
  loading.value = false
}

function retry() {
  void load()
}

onMounted(load)
watch(
  () => route.query.q,
  () => {
    if (route.name === 'search') load()
  },
)
</script>

<template>
  <div class="page search-page">
    <h1 class="page-title">
      {{ query ? 'Результаты поиска' : 'Поиск' }}
    </h1>

    <div v-if="error" class="error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="retry">Повторить</button>
    </div>

    <div v-if="loading" class="loading">
      <div v-for="n in 4" :key="n" class="result-row-skeleton">
        <div class="skeleton thumb-skeleton"></div>
        <div class="result-row-skeleton-lines">
          <div class="skeleton line-skeleton"></div>
          <div class="skeleton line-skeleton short"></div>
        </div>
      </div>
    </div>

    <template v-else-if="result">
      <!-- Channels -->
      <section v-if="result.channels.length" class="channels-section">
        <h2 class="section-title">Каналы</h2>
        <ul class="channel-list">
          <li v-for="c in result.channels" :key="c.id">
            <RouterLink
              :to="{ name: 'channel', params: { id: c.id } }"
              class="channel-row"
            >
              <span class="channel-avatar">
                {{ (c.username || '?').charAt(0).toUpperCase() }}
              </span>
              <span class="channel-text">
                <span class="channel-name">{{ c.username }}</span>
                <span class="channel-meta">
                  {{ formatSubscribers(c.subscriber_count) }}
                </span>
              </span>
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- Videos: horizontal rows -->
      <section class="videos-section">
        <div v-if="result.videos.length" class="result-list">
          <div v-for="v in result.videos" :key="v.id" class="result-row">
            <RouterLink
              :to="{ name: 'watch', params: { id: v.id } }"
              class="result-thumb-link"
            >
              <span class="result-thumb-wrap">
                <img
                  class="result-thumb"
                  :src="`/api/videos/${v.id}/poster`"
                  alt=""
                  loading="lazy"
                />
                <span v-if="v.duration_seconds" class="result-duration">
                  {{ formatDuration(v.duration_seconds) }}
                </span>
              </span>
            </RouterLink>
            <div class="result-info">
              <RouterLink
                :to="{ name: 'watch', params: { id: v.id } }"
                class="result-title"
              >
                {{ v.title }}
              </RouterLink>
              <div class="result-meta">
                {{ formatViews(v.views) }} • {{ timeAgo(v.created_at) }}
              </div>
              <RouterLink
                v-if="v.owner"
                :to="{ name: 'channel', params: { id: v.owner.id } }"
                class="result-channel"
              >
                <span class="result-avatar">
                  {{ (v.owner.username || '?').charAt(0).toUpperCase() }}
                </span>
                <span>{{ v.owner.username }}</span>
              </RouterLink>
              <p v-if="v.description" class="result-desc">{{ v.description }}</p>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-else-if="!result.channels.length" class="empty-state">
          <SearchIcon :size="48" />
          <h2>Ничего не найдено</h2>
          <p>Попробуйте другие ключевые слова.</p>
        </div>
      </section>
    </template>

    <div v-else-if="!error && !query" class="empty-state">
      <SearchIcon :size="48" />
      <h2>Введите поисковый запрос</h2>
      <p>Используйте строку поиска вверху страницы, чтобы найти видео и каналы.</p>
    </div>
  </div>
</template>

<style scoped>
/* ---- Result rows ---- */
.result-list {
  display: flex;
  flex-direction: column;
  max-width: 1100px;
}

.result-row {
  display: flex;
  gap: 16px;
  padding: 16px 0;
  align-items: flex-start;
}

.result-thumb-link {
  flex-shrink: 0;
  width: 360px;
  max-width: 100%;
}

.result-thumb-wrap {
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  background: var(--surface);
}

.result-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.result-duration {
  position: absolute;
  right: 4px;
  bottom: 4px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  line-height: 14px;
  border-radius: 4px;
  padding: 1px 4px;
}

.result-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-title {
  font-size: 18px;
  font-weight: 400;
  line-height: 24px;
  color: var(--text);
  text-decoration: none;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-meta {
  font-size: 12px;
  line-height: 18px;
  color: var(--text-2);
}

.result-channel {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-2);
  text-decoration: none;
  margin-top: 4px;
  width: fit-content;
}

.result-channel:hover {
  color: var(--text);
}

.result-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--surface);
  color: var(--text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;
  user-select: none;
}

.result-desc {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 18px;
  color: var(--text-2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 792px) {
  .result-row {
    flex-direction: column;
  }

  .result-thumb-link {
    width: 100%;
  }
}

/* ---- Channels ---- */
.channels-section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  margin: 8px 0 12px;
}

.channel-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
}

.channel-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  color: var(--text);
  text-decoration: none;
}

.channel-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--surface);
  color: var(--text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 500;
  flex-shrink: 0;
  user-select: none;
}

.channel-text {
  display: flex;
  flex-direction: column;
}

.channel-name {
  font-size: 16px;
  font-weight: 500;
}

.channel-meta {
  color: var(--text-2);
  font-size: 12px;
}

/* ---- Empty state ---- */
.empty-state svg {
  color: var(--text-2);
  margin-bottom: 12px;
}

/* ---- Skeletons ---- */
.result-row-skeleton {
  display: flex;
  gap: 16px;
  padding: 16px 0;
  max-width: 1100px;
}

.thumb-skeleton {
  width: 360px;
  max-width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  flex-shrink: 0;
}

.result-row-skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 8px;
}

.result-row-skeleton-lines .line-skeleton {
  height: 16px;
}

.result-row-skeleton-lines .line-skeleton.short {
  width: 60%;
}
</style>
