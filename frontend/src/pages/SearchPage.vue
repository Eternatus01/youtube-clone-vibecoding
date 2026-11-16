<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { components } from '../api/schema'
import VideoCard from '../components/VideoCard.vue'
import { formatViews } from '../utils/format'

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
    error.value = 'Search failed. Please try again.'
    result.value = null
  } else {
    result.value = data
  }
  loading.value = false
}

function retry() {
  load()
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
      {{ query ? `Results for “${query}”` : 'Search' }}
    </h1>

    <div v-if="error" class="error-banner">
      {{ error }}
      <button class="btn" style="margin-left: 12px" @click="retry">Retry</button>
    </div>

    <div v-if="loading" class="loading">
      <div class="channel-skeleton">
        <div class="skeleton avatar-skeleton"></div>
        <div class="skeleton line-skeleton"></div>
      </div>
      <div class="grid">
        <div v-for="n in 8" :key="n" class="card-skeleton">
          <div class="skeleton thumb-skeleton"></div>
          <div class="skeleton line-skeleton"></div>
          <div class="skeleton line-skeleton short"></div>
        </div>
      </div>
    </div>

    <template v-else-if="result">
      <!-- Channels -->
      <section v-if="result.channels.length" class="channels-section">
        <h2 class="section-title">Channels</h2>
        <ul class="channel-list">
          <li v-for="c in result.channels" :key="c.id">
            <RouterLink
              :to="{ name: 'channel', params: { id: c.id } }"
              class="channel-row"
            >
              <span class="avatar">
                {{ (c.username || '?').charAt(0).toUpperCase() }}
              </span>
              <span class="channel-text">
                <span class="channel-name">{{ c.username }}</span>
                <span class="channel-meta">
                  {{ formatViews(c.subscriber_count).replace(' views', ' subscribers') }}
                </span>
              </span>
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- Videos -->
      <section class="videos-section">
        <h2 v-if="result.channels.length" class="section-title">Videos</h2>
        <div v-if="result.videos.length" class="grid">
          <VideoCard v-for="v in result.videos" :key="v.id" :video="v" />
        </div>
        <div v-else-if="!result.channels.length" class="empty-state">
          <h2>No results found</h2>
          <p>Try a different search term.</p>
        </div>
      </section>
    </template>

    <div v-else-if="!error && !query" class="empty-state">
      <h2>Type something to search</h2>
      <p>Use the search bar above to find videos and channels.</p>
    </div>
  </div>
</template>

<style scoped>
.channels-section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 15px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.channel-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.channel-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  border-radius: 12px;
  color: var(--text);
}

.channel-row:hover {
  background: var(--bg-elevated);
}

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--bg-elevated);
  color: var(--text);
  font-weight: 600;
  font-size: 22px;
  flex-shrink: 0;
  user-select: none;
}

.channel-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.channel-name {
  font-weight: 600;
  font-size: 15px;
}

.channel-meta {
  color: var(--text-secondary);
  font-size: 13px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px 16px;
}

/* Skeletons */
.channel-skeleton {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
  max-width: 360px;
}

.avatar-skeleton {
  width: 56px;
  height: 56px;
  border-radius: 50%;
}

.channel-skeleton .line-skeleton {
  flex: 1;
  height: 16px;
}

.card-skeleton .thumb-skeleton {
  aspect-ratio: 16 / 9;
  border-radius: 12px;
}

.card-skeleton .line-skeleton {
  height: 14px;
  margin-top: 10px;
}

.card-skeleton .line-skeleton.short {
  width: 60%;
}
</style>
