<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ChevronDown, ChevronUp, ListVideo, X } from 'lucide-vue-next'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'
import { useAuthStore } from '../stores/auth'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { formatDuration, formatViews } from '../utils/format'

type PlaylistDetail = components['schemas']['PlaylistDetail']
type PlaylistItemOut = components['schemas']['PlaylistItemOut']

const route = useRoute()
const auth = useAuthStore()

const playlist = ref<PlaylistDetail | null>(null)
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const posterFailed = ref<Record<string, boolean>>({})

// Pending item for the remove confirmation dialog.
const removeTarget = ref<PlaylistItemOut | null>(null)

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
    error.value = extractError(apiError, 'Не удалось загрузить плейлист')
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
    actionError.value = extractError(apiError, 'Не удалось удалить видео из плейлиста')
    return
  }
  playlist.value = {
    ...playlist.value,
    items: playlist.value.items.filter((i) => i.id !== item.id),
    item_count: Math.max(0, playlist.value.item_count - 1),
  }
}

function askRemove(item: PlaylistItemOut) {
  actionError.value = ''
  removeTarget.value = item
}

async function confirmRemove() {
  const item = removeTarget.value
  removeTarget.value = null
  if (item) await removeItem(item)
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
    actionError.value = extractError(apiError, 'Не удалось изменить порядок')
    await load() // Resync from server.
  }
}

onMounted(load)
watch(playlistId, load)
</script>

<template>
  <div class="page">
    <!-- Loading: header + item rows matching real geometry -->
    <div v-if="loading" aria-hidden="true">
      <div class="playlist-header">
        <div class="line-skeleton w40"></div>
        <div class="line-skeleton w60"></div>
        <div class="line-skeleton short"></div>
      </div>
      <div class="item-list">
        <div v-for="n in 6" :key="n" class="item item-skeleton">
          <span class="index">{{ n }}</span>
          <div class="thumb-skeleton"></div>
          <div class="item-info">
            <div class="line-skeleton w60"></div>
            <div class="line-skeleton w40"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="load-error">
      <p>{{ error }}</p>
      <button class="btn" type="button" @click="load">Повторить</button>
    </div>

    <template v-else-if="playlist">
      <header class="playlist-header">
        <p class="kicker">Плейлист</p>
        <h1 class="title">{{ playlist.title }}</h1>
        <p class="meta">
          <RouterLink
            v-if="playlist.owner"
            :to="`/channel/${playlist.owner_id}`"
            class="owner-link"
          >{{ playlist.owner.username }}</RouterLink>
          <span v-if="playlist.owner"> · </span>
          <span>{{ playlist.item_count }} видео</span>
        </p>
        <p v-if="playlist.description" class="description">{{ playlist.description }}</p>
      </header>

      <p v-if="actionError" class="action-error">{{ actionError }}</p>

      <ul v-if="playlist.items.length" class="item-list">
        <li v-for="(item, index) in playlist.items" :key="item.id" class="item">
          <span class="index">{{ index + 1 }}</span>

          <RouterLink class="thumb-link" :to="`/watch/${item.video_id}`">
            <div class="thumb">
              <img
                v-if="!posterFailed[item.id]"
                :src="`/api/videos/${item.video_id}/poster`"
                alt=""
                loading="lazy"
                @error="posterFailed[item.id] = true"
              />
              <span
                v-if="item.video?.duration_seconds"
                class="duration"
              >{{ formatDuration(item.video.duration_seconds) }}</span>
            </div>
          </RouterLink>

          <div class="item-info">
            <RouterLink class="title-link" :to="`/watch/${item.video_id}`">
              <h3 class="item-title">{{ item.video?.title ?? 'Видео' }}</h3>
            </RouterLink>
            <RouterLink
              v-if="item.video?.owner"
              class="channel-link"
              :to="`/channel/${item.video.owner_id}`"
            >{{ item.video.owner.username }}</RouterLink>
            <p class="item-meta">
              {{ formatViews(item.video?.views) }}
              <template v-if="item.video?.duration_seconds">
                • {{ formatDuration(item.video.duration_seconds) }}
              </template>
            </p>
          </div>

          <div v-if="isOwner" class="item-actions">
            <button
              class="icon-btn"
              title="Переместить вверх"
              :disabled="index === 0"
              @click="moveItem(item, -1)"
            >
              <ChevronUp class="lucide-icon" :size="18" />
            </button>
            <button
              class="icon-btn"
              title="Переместить вниз"
              :disabled="index === playlist.items.length - 1"
              @click="moveItem(item, 1)"
            >
              <ChevronDown class="lucide-icon" :size="18" />
            </button>
            <button
              class="icon-btn remove"
              title="Удалить из плейлиста"
              @click="askRemove(item)"
            >
              <X class="lucide-icon" :size="18" />
            </button>
          </div>
        </li>
      </ul>

      <div v-else class="empty-state">
        <ListVideo class="lucide-icon" :size="48" />
        <p>Плейлист пуст</p>
      </div>
    </template>

    <ConfirmDialog
      :open="!!removeTarget"
      title="Удалить из плейлиста"
      :message="removeTarget?.video?.title
        ? `«${removeTarget.video.title}» будет удалён из плейлиста.`
        : 'Видео будет удалено из плейлиста.'"
      confirm-text="Удалить"
      @confirm="confirmRemove"
      @cancel="removeTarget = null"
    />
  </div>
</template>

<style scoped>
.page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

/* ---- Header: kicker + name 20/700 + owner + count ---- */
.playlist-header {
  margin-bottom: 24px;
}

.kicker {
  color: var(--text-2);
  font-size: 14px;
  font-weight: 500;
}

.title {
  font-size: 20px;
  font-weight: 700;
  margin: 2px 0 4px;
}

.meta {
  color: var(--text-2);
  font-size: 14px;
}

.owner-link {
  color: var(--text-2);
}

.owner-link:hover {
  color: var(--text);
}

.description {
  margin-top: 8px;
  color: var(--text-2);
  white-space: pre-wrap;
}

/* ---- List items: horizontal row, thumb 168x94 radius 8 ---- */
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
  border-bottom: 1px solid var(--divider);
}

.index {
  width: 24px;
  text-align: center;
  color: var(--text-2);
  font-size: 13px;
  flex-shrink: 0;
}

.thumb-link {
  flex-shrink: 0;
}

.thumb {
  position: relative;
  width: 168px;
  height: 94px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
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
  flex: 1;
}

.item-title {
  font-weight: 500;
  font-size: 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.title-link {
  color: var(--text);
}

.channel-link {
  display: inline-block;
  color: var(--text-2);
  font-size: 12px;
  margin-top: 4px;
}

.channel-link:hover {
  color: var(--text);
}

.item-meta {
  color: var(--text-2);
  font-size: 12px;
  margin-top: 4px;
}

.item-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.item-actions .remove {
  color: var(--text-2);
}

.item-actions .remove:hover {
  color: var(--danger);
}

/* ---- Empty / error ---- */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 64px 16px;
  color: var(--text-2);
  text-align: center;
}

.load-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 64px 16px;
  color: var(--text-2);
  text-align: center;
}

.load-error p {
  max-width: 480px;
}

.action-error {
  color: var(--danger);
  font-size: 13px;
  margin: -12px 0 12px;
}

/* ---- Skeletons: same geometry as real rows ---- */
.line-skeleton {
  height: 14px;
  border-radius: 6px;
  background: linear-gradient(
    90deg,
    var(--surface) 25%,
    var(--surface-hover) 50%,
    var(--surface) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

.playlist-header .line-skeleton {
  margin-bottom: 8px;
}

.playlist-header .line-skeleton:first-child {
  height: 14px;
}

.playlist-header .line-skeleton:nth-child(2) {
  height: 24px;
  width: 60%;
}

.playlist-header .line-skeleton.short {
  width: 40%;
}

.thumb-skeleton {
  width: 168px;
  height: 94px;
  border-radius: 8px;
  flex-shrink: 0;
  background: linear-gradient(
    90deg,
    var(--surface) 25%,
    var(--surface-hover) 50%,
    var(--surface) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

.item-skeleton .item-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

@keyframes shimmer {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}

@media (max-width: 560px) {
  .thumb {
    width: 128px;
    height: 72px;
  }

  .thumb-skeleton {
    width: 128px;
    height: 72px;
  }
}
</style>
