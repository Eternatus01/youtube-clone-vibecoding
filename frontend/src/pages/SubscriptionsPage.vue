<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Users, VideoOff } from 'lucide-vue-next'
import { api } from '../api/client'
import type { components } from '../api/schema'
import VideoCard from '../components/VideoCard.vue'
import { useToast } from '../composables/useToast'

type VideoOut = components['schemas']['VideoOut']
type UserOut = components['schemas']['UserOut']

/** Subscription list item: backend SubscriptionOut. */
type SubscriptionItem = {
  id: string
  channel_id: string
  created_at: string
  channel: UserOut | null
}

const toast = useToast()

const tab = ref<'channels' | 'videos'>('channels')

// ---- Channels (subscriptions list) ----
const channels = ref<SubscriptionItem[]>([])
const channelsLoading = ref(true)
const channelsError = ref('')
const channelsLoaded = ref(false)
const unsubscribingId = ref<string | null>(null)

/** channel_id -> subscriber count, enriched after the list loads. */
const subCounts = ref<Record<string, number | null>>({})

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
    void enrichCounts(channels.value)
  }
  channelsLoaded.value = true
  channelsLoading.value = false
}

/** Fetch subscriber counts per channel (N+1 is fine for a personal subscription list). */
async function enrichCounts(list: SubscriptionItem[]) {
  await Promise.allSettled(
    list.map(async (item) => {
      const { data } = await api.GET('/api/channels/{channel_id}', {
        params: { path: { channel_id: item.channel_id } },
      })
      subCounts.value[item.channel_id] = data ? data.subscriber_count : null
    }),
  )
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
    toast.push(
      `Вы отписались от канала ${item.channel?.username ?? 'автора'}`,
    )
  } else {
    toast.push('Не удалось отписаться. Попробуйте ещё раз.')
  }
  unsubscribingId.value = null
}

/** 1205 -> "1,2 тыс. подписчиков"; 3 -> "3 подписчика" */
function formatSubs(count: number | null | undefined): string {
  if (count == null || !Number.isFinite(count) || count < 0) return ''
  const forms: [string, string, string] = ['подписчик', 'подписчика', 'подписчиков']
  function plural(n: number): string {
    const n10 = n % 10
    const n100 = n % 100
    if (n10 === 1 && n100 !== 11) return forms[0]
    if (n10 >= 2 && n10 <= 4 && (n100 < 12 || n100 > 14)) return forms[1]
    return forms[2]
  }
  if (count < 1000) {
    const n = Math.round(count)
    return `${n} ${plural(n)}`
  }
  const k = count / 1000
  const short = (k < 100 ? k.toFixed(1) : String(Math.round(k))).replace('.', ',')
  if (short.endsWith(',0')) return `${short.slice(0, -2)} тыс. подписчиков`
  return `${short} тыс. подписчиков`
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
        Лента
      </button>
    </div>

    <!-- Channels -->
    <div v-if="tab === 'channels'">
      <div v-if="channelsError" class="error-banner">
        {{ channelsError }}
        <button class="btn retry-btn" @click="loadChannels">Повторить</button>
      </div>

      <div v-if="channelsLoading" class="channel-list" aria-hidden="true">
        <div v-for="i in 5" :key="i" class="channel-row channel-row-skeleton">
          <div class="skeleton avatar avatar-skeleton"></div>
          <div class="skeleton-line"></div>
        </div>
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
            <span class="channel-text">
              <span class="channel-name">{{ c.channel?.username ?? 'Канал' }}</span>
              <span v-if="subCounts[c.channel_id]" class="channel-subs">
                {{ formatSubs(subCounts[c.channel_id]) }}
              </span>
            </span>
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
        <Users :size="48" stroke-width="1.75" class="empty-icon" />
        <p>Вы ещё не подписаны ни на один канал.</p>
        <RouterLink class="btn action-btn" :to="{ name: 'home' }">Найти каналы</RouterLink>
      </div>
    </div>

    <!-- Feed -->
    <div v-else>
      <div v-if="feedError" class="error-banner">
        {{ feedError }}
        <button class="btn retry-btn" @click="loadFeed">Повторить</button>
      </div>

      <div v-if="feedLoading" class="grid" aria-hidden="true">
        <div v-for="i in 8" :key="i" class="card-skeleton">
          <div class="skeleton thumb-skeleton"></div>
          <div class="skeleton line-skeleton"></div>
          <div class="skeleton line-skeleton short"></div>
        </div>
      </div>

      <template v-else-if="!feedError">
        <div v-if="videos.length" class="grid">
          <VideoCard v-for="v in videos" :key="v.id" :video="v" />
        </div>

        <div v-else class="empty-state">
          <VideoOff :size="48" stroke-width="1.75" class="empty-icon" />
          <p>Новых видео от ваших подписок нет.</p>
          <RouterLink class="btn action-btn" :to="{ name: 'home' }">На главную</RouterLink>
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
  border-bottom: 1px solid var(--divider);
  margin-bottom: 20px;
}

.tab {
  padding: 0 16px;
  height: 40px;
  border: none;
  background: none;
  color: var(--text-2);
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.15s ease;
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
  background: var(--surface-hover);
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
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  background: var(--surface);
}

.avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text);
  font-size: 16px;
  font-weight: 500;
  user-select: none;
}

.channel-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.channel-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.channel-subs {
  font-size: 12px;
  color: var(--text-2);
}

.unsubscribe-btn {
  flex-shrink: 0;
}

/* Skeletons */
.channel-row-skeleton {
  align-items: center;
  gap: 12px;
}

.avatar-skeleton {
  border-radius: 50%;
}

.skeleton-line {
  height: 14px;
  flex: 0 0 180px;
}

.card-skeleton {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.thumb-skeleton {
  aspect-ratio: 16 / 9;
  width: 100%;
}

.line-skeleton {
  height: 14px;
  width: 90%;
}

.line-skeleton.short {
  width: 55%;
}

/* Empty states */
.empty-icon {
  color: var(--text-2);
  margin-bottom: 12px;
}

.empty-state p {
  margin-bottom: 16px;
}

.action-btn {
  display: inline-flex;
  border-radius: 18px;
  height: 40px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px 16px;
}

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

@media (max-width: 792px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
