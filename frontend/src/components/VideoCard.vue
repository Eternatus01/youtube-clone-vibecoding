<script setup lang="ts">
import { computed, ref } from 'vue'
import { formatDuration, formatViews, timeAgo } from '../utils/format'

/** Minimal shape every card renders; VideoOut and SearchVideoOut both satisfy it. */
type VideoCardVideo = {
  id: string
  title: string
  views: number
  duration_seconds?: number | null
  created_at: string
  custom_poster_url?: string | null
  owner?: { username?: string; avatar_url?: string | null } | null
}

const props = defineProps<{ video: VideoCardVideo }>()

const posterFailed = ref(false)
const avatarFailed = ref(false)

const posterSrc = computed(() => {
  const version = encodeURIComponent(props.video.custom_poster_url || '')
  return `/api/videos/${props.video.id}/poster?v=${version}`
})
const avatarUrl = computed(() => props.video.owner?.avatar_url ?? '')
const showAvatarImg = computed(() => !!avatarUrl.value && !avatarFailed.value)

const duration = () => formatDuration(props.video.duration_seconds)
const views = () => (props.video.views != null ? formatViews(props.video.views) : null)
const age = () => timeAgo(props.video.created_at)
const username = computed(() => props.video.owner?.username ?? '')
const channel = computed(() => username.value || 'Неизвестный канал')
const initial = computed(() => username.value.charAt(0).toUpperCase())
const meta = computed(() => [views(), age()].filter(Boolean).join(' • '))
</script>

<template>
  <RouterLink :to="{ name: 'watch', params: { id: video.id } }" class="card">
    <div class="thumb">
      <img
        v-if="!posterFailed"
        :src="posterSrc"
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
      <div v-if="showAvatarImg" class="avatar" aria-hidden="true">
        <img
          class="avatar-img"
          :src="avatarUrl"
          alt=""
          loading="lazy"
          @error="avatarFailed = true"
        />
      </div>
      <div v-else-if="initial" class="avatar" aria-hidden="true">{{ initial }}</div>
      <div class="text">
        <div class="title" :title="video.title">{{ video.title }}</div>
        <RouterLink
          v-if="username"
          :to="{ name: 'channel', params: { username } }"
          class="channel"
          @click.stop
        >{{ channel }}</RouterLink>
        <span v-else class="channel">{{ channel }}</span>
        <div v-if="meta" class="meta">{{ meta }}</div>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.card {
  display: block;
  cursor: pointer;
  color: var(--text);
  min-width: 300px;
}

.thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  background: var(--surface);
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
  color: var(--text-2);
}

.duration {
  position: absolute;
  right: 4px;
  bottom: 4px;
  padding: 2px 4px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
}

.info {
  display: flex;
  gap: 12px;
  padding: 12px 0 0;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--surface-hover);
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 500;
  flex-shrink: 0;
  user-select: none;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.text {
  min-width: 0;
}

.title {
  color: var(--text);
  font-weight: 600;
  font-size: 15px;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 4px;
}

.channel {
  display: block;
  color: var(--text-2);
  font-size: 13px;
  line-height: 1.4;
  margin-bottom: 2px;
  width: fit-content;
}

.channel:hover {
  color: var(--text);
}

.meta {
  color: var(--text-2);
  font-size: 13px;
  line-height: 1.4;
}
</style>
