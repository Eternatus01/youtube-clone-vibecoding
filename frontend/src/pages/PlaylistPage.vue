<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { components } from '../api/schema'
import { useAuthStore } from '../stores/auth'
import { formatDuration, formatViews, timeAgo } from '../utils/format'

type PlaylistDetail = components['schemas']['PlaylistDetail']
type PlaylistItemOut = components['schemas']['PlaylistItemOut']

const route = useRoute()
const auth = useAuthStore()

const playlist = ref<PlaylistDetail | null>(null)
const loading = ref(true)
const error = ref('')
const actionError = ref('')

const playlistId = computed(() => String(route.params.id))
const isOwner = computed(
  () => !!auth.user && !!playlist.value && auth.user.id === playlist.value.owner_id,
)

async function load() {
  loading.value = true
  error.value = ''
  const id = playlistId.value
  const { data, error: apiError } = await api.GET('/api/playlists/{playlist_id}', {
    params: { path: { playlist_id: id } },
  })
  if (apiError || !data) {
    error.value = 'Playlist not found or unavailable.'
    playlist.value = null
  } else {
    playlist.value = data
  }
  loading.value = false
}

// ---- Owner actions: remove item, move up/down ----
async function removeItem(item: PlaylistItemOut) {
  if (!playlist.value || !isOwner.value) return
  actionError.value = ''
  const { error: apiError } = await api.DELETE(
    '/api/playlists/{playlist_id}/items/{item_id}',
    {
      params: {
        path: { playlist_id: playlist.value.id, item_id: item.id },
      },
    },
  )
  if (apiError) {
    actionError.value = 'Failed to remove item.'
    return
  }
  playlist.value = {
    ...playlist.value,
    items: playlist.value.items.filter((i) => i.id !== item.id),
    item_count: Math.max(0, playlist.value.item_count - 1),
  }
}

async function moveItem(item: PlaylistItemOut, delta: number) {
  if (!playlist.value || !isOwner.value) return
  const items = playlist.value.items
  const index = items.findIndex((i) => i.id === item.id)
  const target = index + delta
  if (index === -1 || target < 0 || target >= items.length) return

  // Optimistic local reorder.
  const reordered = [...items]
  reordered.splice(target, 0, ...reordered.splice(index, 1))
  const optimistic = reordered.map((i, idx) => ({ ...i, position: idx }))
  playlist.value = { ...playlist.value, items: optimistic }

  const { error: apiError } = await api.PATCH(
    '/api/playlists/{playlist_id}/items/{item_id}/position',
    {
      params: {
        path: { playlist_id: playlist.value.id, item_id: item.id },
      },
      body: { position: target },
    },
  )
  if (apiError) {
    actionError.value = 'Failed to move item.'
    await load() // Resync from server.
  }
}

onMounted(load)
watch(
  () => route.params.id,
  () => {
    if (route.name === 'playlist' && route.params.id) load()
  },
)
</script>

<template>
  <div class="page playlist-page">
    <div v-if="error" class="error-banner">{{ error }}</div>
    <div v-if="actionError" class="error-banner">{{ actionError }}</div>

    <div v-if="loading" class="loading">
      <div class="skeleton line-skeleton"></div>
      <div class="skeleton line-skeleton short"></div>
    </div>

    <template v-else-if="playlist">
      <div class="playlist-header">
        <h1 class="title">{{ playlist.title }}</h1>
        <p class="meta">
          {{ playlist.item_count }} {{ playlist.item_count === 1 ? 'video' : 'videos' }}
          <template v-if="playlist.owner"> • by {{ playlist.owner.username }}</template>
          • Updated {{ timeAgo(playlist.created_at) }}
        </p>
        <p v-if="playlist.description" class="description">{{ playlist.description }}</p>
      </div>

      <ul v-if="playlist.items.length" class="item-list">
        <li v-for="(item, index) in playlist.items" :key="item.id" class="item">
          <span class="index">{{ index + 1 }}</span>
          <RouterLink
            :to="{ name: 'watch', params: { id: item.video_id } }"
            class="item-link"
          >
            <div class="thumb">
              <img
                v-if="item.video"
                :src="`/api/videos/${item.video_id}/poster`"
                :alt="item.video.title"
                loading="lazy"
              />
              <span v-if="item.video && formatDuration(item.video.duration_seconds)" class="duration">
                {{ formatDuration(item.video.duration_seconds) }}
              </span>
            </div>
            <div class="item-info">
              <div class="item-title">
                {{ item.video?.title ?? 'Unavailable video' }}
              </div>
              <div class="item-meta">
                <template v-if="item.video">
                  {{ item.video.owner?.username ?? 'Unknown channel' }}
                  <template v-if="item.video.views != null">
                    • {{ formatViews(item.video.views) }}
                  </template>
                </template>
              </div>
            </div>
          </RouterLink>
          <div v-if="isOwner" class="item-actions">
            <button
              class="icon-btn"
              title="Move up"
              :disabled="index === 0"
              @click="moveItem(item, -1)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M7.41 15.41 12 10.83l4.59 4.58L18 14l-6-6-6 6z" />
              </svg>
            </button>
            <button
              class="icon-btn"
              title="Move down"
              :disabled="index === playlist.items.length - 1"
              @click="moveItem(item, 1)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6z" />
              </svg>
            </button>
            <button class="icon-btn remove" title="Remove" @click="removeItem(item)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
              </svg>
            </button>
          </div>
        </li>
      </ul>

      <div v-else class="empty-state">
        <h2>No videos in this playlist</h2>
        <p>Items added here will appear in this order.</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.playlist-header {
  margin-bottom: 24px;
}

.title {
  font-size: 24px;
  margin-bottom: 4px;
}

.meta {
  color: var(--text-secondary);
  font-size: 14px;
}

.description {
  margin-top: 8px;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.item-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
}

.item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}

.index {
  width: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  flex-shrink: 0;
}

.item-link {
  display: flex;
  gap: 12px;
  flex: 1;
  min-width: 0;
  color: var(--text);
}

.thumb {
  position: relative;
  width: 160px;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-elevated);
  flex-shrink: 0;
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

.item-info {
  min-width: 0;
}

.item-title {
  font-weight: 500;
  font-size: 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-meta {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: 4px;
}

.item-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.item-actions .remove {
  color: var(--text-secondary);
}

.item-actions .remove:hover {
  color: var(--danger);
}

.loading .line-skeleton {
  height: 18px;
  margin-top: 12px;
}

.loading .line-skeleton.short {
  width: 40%;
}
</style>
