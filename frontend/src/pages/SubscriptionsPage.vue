<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api/client'
import type { components } from '../api/schema'
import VideoCard from '../components/VideoCard.vue'

type VideoOut = components['schemas']['VideoOut']
type UserOut = components['schemas']['UserOut']

/** Subscription list item: backend SubscriptionOut. */
type SubscriptionItem = {
  id: string
  channel_id: string
  created_at: string
  channel: UserOut | null
}

const tab = ref<'channels' | 'videos'>('channels')

// ---- Channels (subscriptions list) ----
const channels = ref<SubscriptionItem[]>([])
const channelsLoading = ref(true)
const channelsError = ref('')
const channelsLoaded = ref(false)
const unsubscribingId = ref<string | null>(null)

// ---- Videos (subscription feed) ----
const videos = ref<VideoOut[]>([])
const feedLoading = ref(true)
const feedError = ref('')
const feedLoaded = ref(false)
const feedPage = ref(1)
const feedPages = ref(1)
const loadingMore = ref(false)

const hasMore = ref(false)

async function loadChannels() {
  channelsLoading.value = true
  channelsError.value = ''
  const { data, error: apiError } = await api.GET('/api/subscriptions/', {
    params: { query: { page: 1, page_size: 100 } },
  })
  if (apiError || !data) {
    channelsError.value = 'Не удалось загрузить подписки. Попробуйте ещё раз.'
    channels.value = []
  } else {
    channels.value = (data.items as SubscriptionItem[]) ?? []
  }
  channelsLoaded.value = true
  channelsLoading.value = false
}

async function loadFeed() {
  feedLoading.value = true
  feedError.value = ''
  const { data, error: apiError } = await api.GET('/api/subscriptions/feed', {
    params: { query: { page: 1, page_size: 20 } },
  })
  if (apiError || !data) {
    feedError.value = 'Не удалось загрузить ленту. Попробуйте ещё раз.'
    videos.value = []
  } else {
    videos.value = (data.items as VideoOut[]) ?? []
    feedPage.value = data.page
    feedPages.value = data.pages
    hasMore.value = data.page < data.pages
  }
  feedLoaded.value = true
  feedLoading.value = false
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  const { data } = await api.GET('/api/subscriptions/feed', {
    params: { query: { page: feedPage.value + 1, page_size: 20 } },
  })
  if (data) {
    videos.value.push(...((data.items as VideoOut[]) ?? []))
    feedPage.value = data.page
    feedPages.value = data.pages
    hasMore.value = data.page < data.pages
  }
  loadingMore.value = false
}

function switchTab(next: 'channels' | 'videos') {
  tab.value = next
  if (next === 'channels' && !channelsLoaded.value) void loadChannels()
  if (next === 'videos' && !feedLoaded.value) void loadFeed()
}

async function unsubscribe(item: SubscriptionItem) {
  if (unsubscribingId.value) return
  unsubscribingId.value = item.channel_id
  // Generated path: /api/channels/{channel_id}/subscribe (DELETE = unsubscribe).
  const { error: apiError } = await api.DELETE('/api/channels/{channel_id}/subscribe', {
    params: { path: { channel_id: item.channel_id } },
  })
  if (!apiError) {
    channels.value = channels.value.filter((c) => c.channel_id !== item.channel_id)
  }
  unsubscribingId.value = null
}

function initial(username: string | undefined): string {
  return (username ?? '?').slice(0, 1).toUpperCase()
}

onMounted(loadChannels)
</script>

<template>
  <div class="page">
    <h1 class="page-title">Подписки</h1>

    <div class="tabs" role="tablist">
      <button
        type="button"
        class="tab"
        :class="{ active: tab === 'channels' }"
        role="tab"
        :aria-selected="tab === 'channels'"
        @click="switchTab('channels')"
      >
        Каналы
      </button>
      <button
        type="button"
        class="tab"
        :class="{ active: tab === 'videos' }"
        role="tab"
        :aria-selected="tab === 'videos'"
        @click="switchTab('videos')"
      >
        Видео
      </button>
    </div>

    <!-- Channels -->
    <div v-if="tab === 'channels'">
      <div v-if="channelsError" class="error-banner">
        {{ channelsError }}
        <button class="btn retry-btn" @click="loadChannels">Повторить</button>
      </div>

      <div v-if="channelsLoading" class="spinner-wrap">
        <span class="spinner" role="status" aria-label="Загрузка"></span>
      </div>

      <div v-else-if="channels.length" class="channel-list">
        <div v-for="c in channels" :key="c.id" class="channel-row">
          <RouterLink
            class="channel-info"
            :to="{ name: 'channel', params: { id: c.channel_id } }"
          >
            <img
              v-if="c.channel?.avatar_url"
              class="avatar"
              :src="c.channel.avatar_url"
              :alt="c.channel.username"
              loading="lazy"
            />
            <span v-else class="avatar avatar-fallback">
              {{ initial(c.channel?.username) }}
            </span>
            <span class="channel-name">{{ c.channel?.username ?? 'Канал' }}</span>
          </RouterLink>
          <button
            type="button"
            class="btn unsubscribe-btn"
            :disabled="unsubscribingId === c.channel_id"
            @click="unsubscribe(c)"
          >
            {{ unsubscribingId === c.channel_id ? '…' : 'Отписаться' }}
          </button>
        </div>
      </div>

      <div v-else-if="!channelsError" class="empty-state">
        <p>Вы ещё не подписаны ни на один канал.</p>
      </div>
    </div>

    <!-- Videos -->
    <div v-else>
      <div v-if="feedError" class="error-banner">
        {{ feedError }}
        <button class="btn retry-btn" @click="loadFeed">Повторить</button>
      </div>

      <div v-if="feedLoading" class="spinner-wrap">
        <span class="spinner" role="status" aria-label="Загрузка"></span>
      </div>

      <template v-else-if="!feedError">
        <div v-if="videos.length" class="grid">
          <VideoCard v-for="v in videos" :key="v.id" :video="v" />
        </div>

        <div v-else class="empty-state">
          <p>Новых видео от ваших подписок нет.</p>
        </div>

        <div v-if="hasMore" class="load-more">
          <button class="btn" :disabled="loadingMore" @click="loadMore">
            {{ loadingMore ? 'Загрузка…' : 'Загрузить ещё' }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}

.tab {
  padding: 8px 16px;
  border: none;
  background: none;
  color: var(--text-secondary);
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tab:hover {
  color: var(--text);
}

.tab.active {
  color: var(--text);
  border-bottom-color: var(--text);
}

.channel-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 720px;
}

.channel-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 12px;
  border-radius: 12px;
}

.channel-row:hover {
  background: var(--bg-hover);
}

.channel-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  color: inherit;
  text-decoration: none;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  background: var(--bg-elevated);
}

.avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text);
  font-size: 18px;
  font-weight: 600;
}

.channel-name {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.unsubscribe-btn {
  flex-shrink: 0;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px 16px;
}

.spinner-wrap {
  display: flex;
  justify-content: center;
  padding: 64px 0;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>
