<script setup lang="ts">
import { ref } from 'vue'
import { formatDuration, formatViews, timeAgo } from '../utils/format'

/** Minimal shape every card renders; VideoOut and SearchVideoOut both satisfy it. */
type VideoCardVideo = {
  id: string
  title: string
  views: number
  duration_seconds?: number | null
  created_at: string
  owner?: { username?: string } | null
}

const props = defineProps<{ video: VideoCardVideo }>()

const posterFailed = ref(false)

const duration = () => formatDuration(props.video.duration_seconds)
const views = () => (props.video.views != null ? formatViews(props.video.views) : null)
const age = () => timeAgo(props.video.created_at)
const channel = () => props.video.owner?.username ?? 'Unknown channel'
</script>

<template>
  <RouterLink :to="{ name: 'watch', params: { id: video.id } }" class="card">
    <div class="thumb">
      <img
        v-if="!posterFailed"
        :src="`/api/videos/${video.id}/poster`"
        :alt="video.title"
        loading="lazy"
        @error="posterFailed = true"
      />
      <div v-else class="thumb-fallback">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="currentColor">
          <path d="M8 5v14l11-7L8 5z" />
        </svg>
      </div>
      <span v-if="duration()" class="duration">{{ duration() }}</span>
    </div>
    <div class="info">
      <div class="title" :title="video.title">{{ video.title }}</div>
      <div class="channel">{{ channel() }}</div>
      <div class="meta">
        <span v-if="views()">{{ views() }}</span>
        <span v-if="views() && age()">•</span>
        <span v-if="age()">{{ age() }}</span>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.card {
  display: block;
  cursor: pointer;
  border-radius: 12px;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.card:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

.thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  background: var(--bg-elevated);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.duration {
  position: absolute;
  right: 6px;
  bottom: 6px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
}

.info {
  padding: 10px 4px 0;
}

.title {
  font-weight: 500;
  font-size: 14px;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 4px;
}

.channel {
  color: var(--text-secondary);
  font-size: 12px;
  margin-bottom: 2px;
}

.meta {
  color: var(--text-secondary);
  font-size: 12px;
  display: flex;
  gap: 4px;
}
</style>
