<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { components } from '../api/schema'
import { formatDuration, formatViews, timeAgo } from '../utils/format'

type VideoOut = components['schemas']['VideoOut']

const route = useRoute()

const video = ref<VideoOut | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  const id = String(route.params.id)
  const { data, error: apiError } = await api.GET('/api/videos/{video_id}', {
    params: { path: { video_id: id } },
  })
  if (apiError || !data) {
    error.value = 'Video not found or unavailable.'
    video.value = null
  } else {
    video.value = data
  }
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="page watch">
    <div v-if="error" class="error-banner">{{ error }}</div>

    <div v-if="loading" class="loading">
      <div class="skeleton player-skeleton"></div>
      <div class="skeleton line-skeleton"></div>
      <div class="skeleton line-skeleton short"></div>
    </div>

    <template v-else-if="video">
      <!-- Still processing / failed -->
      <div
        v-if="video.status !== 'ready'"
        class="placeholder"
      >
        <template v-if="video.status === 'failed'">
          <h2>Video processing failed</h2>
          <p>This video could not be processed.</p>
        </template>
        <template v-else>
          <h2>{{ video.status === 'processing' ? 'Processing…' : 'Uploading…' }}</h2>
          <p>This video is not ready yet. Please check back later.</p>
        </template>
      </div>

      <video
        v-else
        class="player"
        controls
        preload="metadata"
        :poster="`/api/videos/${video.id}/poster`"
      >
        <source :src="`/api/videos/${video.id}/stream`" type="video/mp4" />
        Your browser does not support video playback.
      </video>

      <h1 class="title">{{ video.title }}</h1>

      <div class="meta-row">
        <RouterLink
          v-if="video.owner"
          :to="{ name: 'channel', params: { id: video.owner.id } }"
          class="channel"
        >
          {{ video.owner.username }}
        </RouterLink>
        <span class="meta">
          {{ formatViews(video.views) }} • {{ timeAgo(video.created_at) }}
          <template v-if="formatDuration(video.duration_seconds)">
            • {{ formatDuration(video.duration_seconds) }}
          </template>
        </span>
      </div>

      <div v-if="video.description" class="description">{{ video.description }}</div>
    </template>
  </div>
</template>

<style scoped>
.watch {
  max-width: 1000px;
}

.player {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  border-radius: 12px;
  display: block;
}

.player-skeleton {
  aspect-ratio: 16 / 9;
  border-radius: 12px;
}

.loading .line-skeleton {
  height: 18px;
  margin-top: 16px;
}

.loading .line-skeleton.short {
  width: 40%;
}

.placeholder {
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  background: var(--bg-elevated);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-secondary);
}

.placeholder h2 {
  color: var(--text);
}

.title {
  font-size: 20px;
  margin-top: 16px;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.channel {
  font-weight: 600;
}

.channel:hover {
  text-decoration: underline;
}

.meta {
  color: var(--text-secondary);
}

.description {
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--bg-elevated);
  border-radius: 12px;
  white-space: pre-wrap;
}
</style>
