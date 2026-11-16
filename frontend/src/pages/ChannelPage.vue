<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { components } from '../api/schema'
import { useAuthStore } from '../stores/auth'
import VideoCard from '../components/VideoCard.vue'
import { formatViews, timeAgo } from '../utils/format'

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
    error.value = 'Channel not found.'
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
      <button class="btn retry-btn" @click="load">Retry</button>
    </div>

    <div v-if="loading" class="header-skeleton">
      <div class="skeleton avatar-skeleton"></div>
      <div class="header-skeleton-lines">
        <div class="skeleton line-skeleton"></div>
        <div class="skeleton line-skeleton short"></div>
      </div>
    </div>

    <template v-else-if="channel">
      <div class="channel-header">
        <span class="avatar avatar-large">
          {{ (channel.username || '?').charAt(0).toUpperCase() }}
        </span>
        <div class="channel-info">
          <h1 class="channel-name">{{ channel.username }}</h1>
          <p class="channel-meta">
            {{ formatViews(channel.subscriber_count).replace(' views', ' subscribers') }}
            • {{ channel.video_count }} {{ channel.video_count === 1 ? 'video' : 'videos' }}
            • Joined {{ timeAgo(channel.created_at) }}
          </p>
          <p v-if="channel.is_subscribed" class="channel-subscribed">
            You are subscribed
          </p>
        </div>
        <button
          v-if="canSubscribe"
          class="btn subscribe-btn"
          :class="{ subscribed: channel.is_subscribed }"
          :disabled="subscribePending"
          @click="toggleSubscribe"
        >
          {{ channel.is_subscribed ? 'Subscribed' : 'Subscribe' }}
        </button>
      </div>

      <div class="tabs" role="tablist">
        <button
          class="tab"
          :class="{ active: tab === 'videos' }"
          role="tab"
          :aria-selected="tab === 'videos'"
          @click="setTab('videos')"
        >
          Videos
        </button>
        <button
          class="tab"
          :class="{ active: tab === 'playlists' }"
          role="tab"
          :aria-selected="tab === 'playlists'"
          @click="setTab('playlists')"
        >
          Playlists
        </button>
      </div>

      <div v-if="tabLoading" class="grid">
        <div v-for="n in 6" :key="n" class="card-skeleton">
          <div class="skeleton thumb-skeleton"></div>
          <div class="skeleton line-skeleton"></div>
        </div>
      </div>

      <template v-else-if="tab === 'videos'">
        <div v-if="videos.length" class="grid">
          <VideoCard v-for="v in videos" :key="v.id" :video="v" />
        </div>
        <div v-else class="empty-state">
          <h2>No videos yet</h2>
          <p>This channel hasn't uploaded anything.</p>
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
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M3 10h11v2H3v-2zm0-4h11v2H3V6zm0 8h7v2H3v-2zm13-1v8l6-4-6-4z" />
                </svg>
              </span>
              <span class="playlist-text">
                <span class="playlist-title">{{ p.title }}</span>
                <span class="playlist-meta">
                  {{ p.item_count }} {{ p.item_count === 1 ? 'video' : 'videos' }}
                  • {{ timeAgo(p.created_at) }}
                </span>
              </span>
            </RouterLink>
          </li>
        </ul>
        <div v-else class="empty-state">
          <h2>No playlists</h2>
          <p>This channel hasn't created any playlists.</p>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.channel-header {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--bg-elevated);
  color: var(--text);
  font-weight: 600;
  flex-shrink: 0;
  user-select: none;
}

.avatar-large {
  width: 96px;
  height: 96px;
  font-size: 40px;
}

.channel-info {
  flex: 1;
  min-width: 200px;
}

.channel-name {
  font-size: 24px;
  margin-bottom: 4px;
}

.channel-meta {
  color: var(--text-secondary);
  font-size: 14px;
}

.channel-subscribed {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: 4px;
}

.subscribe-btn {
  align-self: center;
}

.subscribe-btn.subscribed {
  background: var(--bg-elevated);
  color: var(--text-secondary);
}

/* ---- Tabs ---- */
.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin: 24px 0;
}

.tab {
  padding: 10px 18px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.tab:hover {
  color: var(--text);
}

.tab.active {
  color: var(--text);
  border-bottom-color: var(--accent);
}

/* ---- Grid ---- */
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
  background: var(--bg-elevated);
  color: var(--text);
}

.playlist-link:hover {
  background: var(--bg-hover);
}

.playlist-icon {
  color: var(--text-secondary);
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
  color: var(--text-secondary);
  font-size: 12px;
}

/* ---- Skeletons ---- */
.header-skeleton {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-skeleton .avatar-skeleton {
  width: 96px;
  height: 96px;
  border-radius: 50%;
}

.header-skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.header-skeleton-lines .line-skeleton.short {
  width: 40%;
}
</style>
