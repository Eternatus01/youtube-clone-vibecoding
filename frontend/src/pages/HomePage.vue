<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { components } from '../api/schema'
import VideoCard from '../components/VideoCard.vue'

type VideoOut = components['schemas']['VideoOut']

const route = useRoute()

const videos = ref<VideoOut[]>([])
const loading = ref(true)
const error = ref('')
const search = ref('')

async function load() {
  loading.value = true
  error.value = ''
  search.value = typeof route.query.search === 'string' ? route.query.search : ''

  const { data, error: apiError } = await api.GET('/api/videos/', {
    params: {
      query: {
        page: 1,
        page_size: 20,
        ...(search.value ? { search: search.value } : {}),
      },
    },
  })

  if (apiError || !data) {
    error.value = 'Failed to load videos. Please try again.'
    videos.value = []
  } else {
    // Backend PaginatedResponse.items is untyped; the list endpoint returns videos.
    videos.value = (data.items as VideoOut[]) ?? []
  }
  loading.value = false
}

function retry() {
  load()
}

onMounted(load)
watch(
  () => route.query.search,
  () => {
    if (route.name === 'home') load()
  },
)
</script>

<template>
  <div class="page">
    <h1 v-if="search" class="page-title">Results for “{{ search }}”</h1>
    <h1 v-else class="page-title">Recommended</h1>

    <div v-if="error" class="error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="retry">Retry</button>
    </div>

    <div v-if="loading" class="grid">
      <div v-for="n in 8" :key="n" class="card-skeleton">
        <div class="skeleton thumb-skeleton"></div>
        <div class="skeleton line-skeleton"></div>
        <div class="skeleton line-skeleton short"></div>
      </div>
    </div>

    <div v-else-if="videos.length" class="grid">
      <VideoCard v-for="v in videos" :key="v.id" :video="v" />
    </div>

    <div v-else-if="!error" class="empty-state">
      <h2>{{ search ? 'No results found' : 'No videos yet' }}</h2>
      <p>
        {{
          search
            ? 'Try a different search term.'
            : 'Be the first to upload a video!'
        }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px 16px;
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
