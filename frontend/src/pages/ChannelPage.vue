<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ListVideo, Pencil, VideoOff } from 'lucide-vue-next'
import { api } from '../api/client'
import type { components } from '../api/schema'
import { useAuthStore } from '../stores/auth'
import VideoCard from '../components/VideoCard.vue'
import { formatSubscribers, timeAgo } from '../utils/format'

type ChannelOut = components['schemas']['ChannelOut']
type VideoOut = components['schemas']['VideoOut']
type PlaylistOut = components['schemas']['PlaylistOut']

const route = useRoute()
const auth = useAuthStore()

const channel = ref<ChannelOut | null>(null)
const videos = ref<VideoOut[]>([])
const playlists = ref<PlaylistOut[]>([])
const loading = ref(true)
const error = ref('')
const tab = ref<'videos' | 'playlists'>('videos')
const tabLoading = ref(false)

const channelId = computed(() => String(route.params.id))
const isOwner = computed(
  () => !!auth.user && !!channel.value && auth.user.id === channel.value.id,
)
const canSubscribe = computed(() => !!auth.user && !isOwner.value)

async function load() {
  loading.value = true
  error.value = ''
  channel.value = null
  videos.value = []
  playlists.value = []
  const id = channelId.value
  const { data, error: apiError } = await api.GET('/api/channels/{channel_id}', {
    params: { path: { channel_id: id } },
  })
  if (apiError || !data) {
    error.value = 'Канал не найден.'
    loading.value = false
    return
  }
  channel.value = data
  loading.value = false
  void loadTab()
}

async function loadTab() {
  if (!channel.value) return
  tabLoading.value = true
  const id = channel.value.id
  if (tab.value === 'videos') {
    const { data } = await api.GET('/api/channels/{channel_id}/videos', {
      params: { path: { channel_id: id }, query: { page: 1, page_size: 40 } },
    })
    // Backend PaginatedResponse.items is untyped; this endpoint returns videos.
    videos.value = (data?.items as VideoOut[]) ?? []
  } else {
    const { data } = await api.GET('/api/channels/{channel_id}/playlists', {
      params: { path: { channel_id: id }, query: { page: 1, page_size: 40 } },
    })
    playlists.value = (data?.items as PlaylistOut[]) ?? []
  }
  tabLoading.value = false
}

function setTab(t: 'videos' | 'playlists') {
  if (tab.value === t) return
  tab.value = t
  void loadTab()
}

const subscribePending = ref(false)

async function toggleSubscribe() {
  if (!canSubscribe.value || !channel.value || subscribePending.value) return
  subscribePending.value = true
  const id = channel.value.id
  const wasSubscribed = channel.value.is_subscribed === true

  // Optimistic.
  channel.value = {
    ...channel.value,
    is_subscribed: !wasSubscribed,
    subscriber_count: Math.max(
      0,
      channel.value.subscriber_count + (wasSubscribed ? -1 : 1),
    ),
  }

  const { error: apiError } = wasSubscribed
    ? await api.DELETE('/api/channels/{channel_id}/subscribe', {
        params: { path: { channel_id: id } },
      })
    : await api.POST('/api/channels/{channel_id}/subscribe', {
        params: { path: { channel_id: id } },
      })
  subscribePending.value = false
  if (apiError) {
    const { data } = await api.GET('/api/channels/{channel_id}', {
      params: { path: { channel_id: id } },
    })
    if (data) channel.value = data
  }
}

onMounted(load)
watch(
  () => route.params.id,
  () => {
    if (route.name === 'channel' && route.params.id) load()
  },
)
</script>

<template>
  <div class="page channel-page">
    <div v-if="error" class="error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="load">Повторить</button>
    </div>

    <div v-if="loading" class="channel-skeleton">
      <div class="skeleton banner-skeleton"></div>
      <div class="head-skeleton">
        <div class="skeleton avatar-skeleton"></div>
        <div class="head-skeleton-lines">
          <div class="skeleton line-skeleton"></div>
          <div class="skeleton line-skeleton short"></div>
        </div>
      </div>
      <div class="grid">
        <div v-for="n in 8" :key="n" class="card-skeleton">
          <div class="skeleton thumb-skeleton"></div>
          <div class="skeleton line-skeleton"></div>
        </div>
      </div>
    </div>

    <template v-else-if="channel">
      <!-- Banner 16:5: cover image when set, neutral gradient otherwise -->
      <div class="banner" :class="{ 'with-cover': !!channel.cover_url }">
        <img
          v-if="channel.cover_url"
          :src="channel.cover_url"
          :alt="`Обложка канала ${channel.username}`"
          class="cover-img"
        />
      </div>

      <div class="channel-head">
        <span v-if="channel.avatar_url" class="avatar avatar-128">
          <img
            :src="channel.avatar_url"
            :alt="`Аватар канала ${channel.username}`"
            class="avatar-img"
          />
        </span>
        <span v-else class="avatar avatar-128">
          {{ (channel.username || '?').charAt(0).toUpperCase() }}
        </span>
        <div class="channel-info">
          <h1 class="channel-name">{{ channel.username }}</h1>
          <p class="channel-meta">
            <span class="handle">@{{ channel.username }}</span>
            • {{ formatSubscribers(channel.subscriber_count) }}
            • {{ channel.video_count }} видео
          </p>
        </div>
        <div class="head-actions">
          <RouterLink v-if="isOwner" to="/channel/edit" class="pill edit-pill">
            <Pencil :size="16" />
            Редактировать канал
          </RouterLink>
          <button
            v-if="canSubscribe"
            class="pill subscribe-pill"
            :class="{ subscribed: channel.is_subscribed }"
            :disabled="subscribePending"
            @click="toggleSubscribe"
          >
            {{ channel.is_subscribed ? 'Вы подписаны' : 'Подписаться' }}
          </button>
        </div>
      </div>

      <div class="tabs" role="tablist">
        <button
          class="tab"
          :class="{ active: tab === 'videos' }"
          role="tab"
          :aria-selected="tab === 'videos'"
          @click="setTab('videos')"
        >
          Видео
        </button>
        <button
          class="tab"
          :class="{ active: tab === 'playlists' }"
          role="tab"
          :aria-selected="tab === 'playlists'"
          @click="setTab('playlists')"
        >
          Плейлисты
        </button>
      </div>

      <div v-if="tabLoading" class="grid">
        <div v-for="n in 8" :key="n" class="card-skeleton">
          <div class="skeleton thumb-skeleton"></div>
          <div class="skeleton line-skeleton"></div>
        </div>
      </div>

      <template v-else-if="tab === 'videos'">
        <div v-if="videos.length" class="grid">
          <VideoCard v-for="v in videos" :key="v.id" :video="v" />
        </div>
        <div v-else class="empty-state">
          <VideoOff :size="48" />
          <h2>Нет видео</h2>
          <p>На этом канале пока нет загруженных видео.</p>
        </div>
      </template>

      <template v-else>
        <ul v-if="playlists.length" class="playlist-list">
          <li v-for="p in playlists" :key="p.id">
            <RouterLink
              :to="{ name: 'playlist', params: { id: p.id } }"
              class="playlist-link"
            >
              <span class="playlist-icon">
                <ListVideo :size="24" />
              </span>
              <span class="playlist-text">
                <span class="playlist-title">{{ p.title }}</span>
                <span class="playlist-meta">
                  {{ p.item_count }} видео • {{ timeAgo(p.created_at) }}
                </span>
              </span>
            </RouterLink>
          </li>
        </ul>
        <div v-else class="empty-state">
          <ListVideo :size="48" />
          <h2>Нет плейлистов</h2>
          <p>На этом канале пока нет плейлистов.</p>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
/* ---- Banner ---- */
.banner {
  width: 100%;
  aspect-ratio: 16 / 5;
  background: var(--surface);
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

/* Gradient placeholder variant (no cover uploaded) */
.banner:not(.with-cover) {
  background: linear-gradient(135deg, var(--surface) 0%, var(--surface-hover) 100%);
}

.cover-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* ---- Head row ---- */
.channel-head {
  display: flex;
  align-items: center;
  gap: 24px;
  padding-top: 12px;
  flex-wrap: wrap;
  position: relative;
  z-index: 1;
}

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--surface);
  color: var(--text);
  font-weight: 500;
  flex-shrink: 0;
  user-select: none;
}

.avatar-128 {
  width: 128px;
  height: 128px;
  font-size: 48px;
  border: 4px solid var(--bg);
  margin-top: -64px;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.channel-info {
  flex: 1;
  min-width: 200px;
}

.channel-name {
  font-size: 36px;
  font-weight: 700;
  line-height: 1.2;
  margin: 0;
}

.channel-meta {
  color: var(--text-2);
  font-size: 14px;
  margin: 4px 0 0;
}

/* ---- Pill (subscribe) ---- */
.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  padding: 0 16px;
  border: none;
  border-radius: 18px;
  background: var(--surface);
  color: var(--text);
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
}

.pill:hover {
  background: var(--surface-hover);
}

.subscribe-pill {
  background: var(--text);
  color: var(--bg);
}

.subscribe-pill:hover {
  background: var(--text);
  opacity: 0.9;
}

.subscribe-pill.subscribed {
  background: var(--surface);
  color: var(--text);
}

.subscribe-pill.subscribed:hover {
  background: var(--surface-hover);
}

/* ---- Edit + subscribe cluster ---- */
.head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.edit-pill {
  text-decoration: none;
}

.edit-pill:hover {
  background: var(--surface-hover);
}

/* ---- Tabs ---- */
.tabs {
  display: flex;
  gap: 24px;
  border-bottom: 1px solid var(--divider);
  margin: 20px 0 24px;
}

.tab {
  padding: 12px 0;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  color: var(--text-2);
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.tab:hover {
  color: var(--text);
}

.tab.active {
  color: var(--text);
  border-bottom-color: var(--text);
}

/* ---- Grid (same as HomePage) ---- */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px 16px;
}

@media (max-width: 792px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

/* ---- Empty state ---- */
.empty-state {
  color: var(--text-2);
}

.empty-state :deep(svg),
.empty-state svg {
  color: var(--text-2);
  margin-bottom: 12px;
}

/* ---- Playlists ---- */
.playlist-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.playlist-link {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--surface);
  color: var(--text);
  text-decoration: none;
}

.playlist-link:hover {
  background: var(--surface-hover);
}

.playlist-icon {
  color: var(--text-2);
  display: flex;
}

.playlist-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.playlist-title {
  font-weight: 500;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-meta {
  color: var(--text-2);
  font-size: 12px;
}

/* ---- Skeletons ---- */
.channel-skeleton {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.banner-skeleton {
  width: 100%;
  aspect-ratio: 16 / 5;
  border-radius: 12px;
}

.head-skeleton {
  display: flex;
  align-items: center;
  gap: 24px;
  padding-top: 12px;
}

.head-skeleton .avatar-skeleton {
  width: 128px;
  height: 128px;
  border-radius: 50%;
  flex-shrink: 0;
}

.head-skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.head-skeleton-lines .line-skeleton {
  height: 24px;
}

.head-skeleton-lines .line-skeleton.short {
  width: 40%;
}

.card-skeleton .thumb-skeleton {
  aspect-ratio: 16 / 9;
  border-radius: 12px;
}

.card-skeleton .line-skeleton {
  height: 14px;
  margin-top: 10px;
}
</style>
