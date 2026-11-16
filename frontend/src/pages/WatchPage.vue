<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Flag, ThumbsDown, ThumbsUp } from 'lucide-vue-next'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'
import {
  formatDuration,
  formatSubscribers,
  formatViews,
  pluralRu,
  timeAgo,
} from '../utils/format'

type VideoOut = components['schemas']['VideoOut']
type ChannelOut = components['schemas']['ChannelOut']
type CommentOut = components['schemas']['CommentOut']
type LikeInfo = components['schemas']['LikeInfo']

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const video = ref<VideoOut | null>(null)
const channel = ref<ChannelOut | null>(null)
const related = ref<VideoOut[]>([])
const loading = ref(true)
const error = ref('')

// ---- Comments ----
const comments = ref<CommentOut[]>([])
const commentsLoading = ref(false)
const commentsPage = ref(1)
const commentsPages = ref(1)
const commentText = ref('')
const postingComment = ref(false)
const commentFocused = ref(false)

// ---- Like state (optimistic) ----
const likePending = ref(false)
const likeStatus = ref<'like' | 'dislike' | null>(null)
const likeCount = ref(0)
const dislikeCount = ref(0)

const videoId = computed(() => String(route.params.id))
const isOwner = computed(
  () => !!video.value && !!auth.user && auth.user.id === video.value.owner_id,
)
const canSubscribe = computed(
  () => !!auth.user && !!channel.value && !isOwner.value,
)

const commentCountLabel = computed(() => {
  const n = video.value?.comment_count ?? comments.value.length
  return `${n} ${pluralRu(n, ['комментарий', 'комментария', 'комментариев'])}`
})

const showCommentActions = computed(
  () => commentFocused.value || commentText.value.trim().length > 0,
)

// ---- Description collapse ----
const descExpanded = ref(false)

// ---- Report (owner never sees the button) ----
const reportOpen = ref(false)
const reportDone = ref(false)
const reportReason = ref('')
const reportSending = ref(false)

function cancelReport() {
  reportOpen.value = false
  reportReason.value = ''
}

async function submitReport() {
  if (!video.value || !reportReason.value.trim() || reportSending.value) return
  reportSending.value = true
  const { error: apiError } = await api.POST('/api/reports/', {
    body: { video_id: video.value.id, reason: reportReason.value.trim() },
  })
  reportSending.value = false
  if (apiError) {
    toast.push(extractError(apiError, 'Не удалось отправить жалобу'))
    return
  }
  reportOpen.value = false
  reportDone.value = true
  reportReason.value = ''
}

async function load() {
  loading.value = true
  error.value = ''
  const id = videoId.value
  const { data, error: apiError } = await api.GET('/api/videos/{video_id}', {
    params: { path: { video_id: id } },
  })
  if (apiError || !data) {
    error.value = 'Видео не найдено или недоступно.'
    video.value = null
    loading.value = false
    return
  }
  video.value = data
  likeStatus.value = data.user_like ?? null
  likeCount.value = data.like_count
  dislikeCount.value = data.dislike_count
  loading.value = false
  descExpanded.value = false

  // Owner channel info (subscribe state) and related videos in parallel.
  if (data.owner) {
    void loadChannel(data.owner.id)
  } else {
    channel.value = null
  }
  void loadRelated(id)
  void loadComments(id, /* reset */ true)
}

async function loadChannel(channelId: string) {
  const { data } = await api.GET('/api/channels/{channel_id}', {
    params: { path: { channel_id: channelId } },
  })
  channel.value = data ?? null
}

async function loadRelated(id: string) {
  const { data } = await api.GET('/api/videos/{video_id}/related', {
    params: { path: { video_id: id }, query: { page: 1, page_size: 12 } },
  })
  // Backend PaginatedResponse.items is untyped; the related endpoint returns videos.
  related.value = (data?.items as VideoOut[]) ?? []
}

async function loadComments(id: string, reset: boolean) {
  commentsLoading.value = true
  const page = reset ? 1 : commentsPage.value + 1
  const { data } = await api.GET('/api/videos/{video_id}/comments/', {
    params: {
      path: { video_id: id },
      query: { page, page_size: 10, sort: 'newest' },
    },
  })
  if (data) {
    const items = (data.items as CommentOut[]) ?? []
    comments.value = reset ? items : [...comments.value, ...items]
    commentsPage.value = data.page
    commentsPages.value = data.pages
  } else if (reset) {
    comments.value = []
  }
  commentsLoading.value = false
}

function showMoreComments() {
  if (!commentsLoading.value && commentsPage.value < commentsPages.value) {
    void loadComments(videoId.value, false)
  }
}

// ---- Like/dislike toggle ----
/**
 * Optimistically apply a vote transition, then reconcile `user_like` with the
 * returned LikeInfo. If the server disagrees with our optimistic guess, the
 * counts may be stale — refetch the video to resync.
 */
async function toggleLike() {
  if (!auth.user || !video.value || likePending.value) return
  likePending.value = true
  const id = video.value.id
  const wasLiked = likeStatus.value === 'like'

  // Optimistic counts.
  if (wasLiked) {
    likeCount.value = Math.max(0, likeCount.value - 1)
    likeStatus.value = null
  } else {
    if (likeStatus.value === 'dislike') {
      dislikeCount.value = Math.max(0, dislikeCount.value - 1)
    }
    likeCount.value += 1
    likeStatus.value = 'like'
  }

  const { data, error: apiError } = wasLiked
    ? await api.DELETE('/api/videos/{video_id}/like', {
        params: { path: { video_id: id } },
      })
    : await api.POST('/api/videos/{video_id}/like', {
        params: { path: { video_id: id } },
      })

  likePending.value = false
  if (apiError || !data) {
    // Revert by reloading the authoritative state.
    toast.push('Не удалось сохранить оценку')
    await resyncVideo(id)
    return
  }
  syncFromLikeInfo(data, wasLiked ? 'like' : null, id)
}

async function toggleDislike() {
  if (!auth.user || !video.value || likePending.value) return
  likePending.value = true
  const id = video.value.id
  const wasDisliked = likeStatus.value === 'dislike'

  // Optimistic counts.
  if (wasDisliked) {
    dislikeCount.value = Math.max(0, dislikeCount.value - 1)
    likeStatus.value = null
  } else {
    if (likeStatus.value === 'like') {
      likeCount.value = Math.max(0, likeCount.value - 1)
    }
    dislikeCount.value += 1
    likeStatus.value = 'dislike'
  }

  const { data, error: apiError } = wasDisliked
    ? await api.DELETE('/api/videos/{video_id}/dislike', {
        params: { path: { video_id: id } },
      })
    : await api.POST('/api/videos/{video_id}/dislike', {
        params: { path: { video_id: id } },
      })

  likePending.value = false
  if (apiError || !data) {
    toast.push('Не удалось сохранить оценку')
    await resyncVideo(id)
    return
  }
  syncFromLikeInfo(data, wasDisliked ? 'dislike' : null, id)
}

function syncFromLikeInfo(info: LikeInfo, wasApplied: 'like' | 'dislike' | null, id: string) {
  const serverStatus = info.like_status ?? null
  likeStatus.value = serverStatus
  // The LikeInfo payload carries no counts; if our optimistic guess matched
  // the server transition they are already right, otherwise resync.
  if (serverStatus === wasApplied) {
    void resyncVideo(id)
  }
}

async function resyncVideo(id: string) {
  const { data } = await api.GET('/api/videos/{video_id}', {
    params: { path: { video_id: id } },
  })
  if (data) {
    video.value = data
    likeStatus.value = data.user_like ?? null
    likeCount.value = data.like_count
    dislikeCount.value = data.dislike_count
  }
}

// ---- Subscribe ----
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

  if (wasSubscribed) {
    const { error: apiError } = await api.DELETE(
      '/api/channels/{channel_id}/subscribe',
      { params: { path: { channel_id: id } } },
    )
    subscribePending.value = false
    if (apiError) await resyncChannel(id)
  } else {
    const { error: apiError } = await api.POST(
      '/api/channels/{channel_id}/subscribe',
      { params: { path: { channel_id: id } } },
    )
    subscribePending.value = false
    if (apiError) await resyncChannel(id)
  }
}

async function resyncChannel(id: string) {
  const { data } = await api.GET('/api/channels/{channel_id}', {
    params: { path: { channel_id: id } },
  })
  if (data) channel.value = data
}

// ---- Comments: post & delete ----
async function postComment() {
  const body = commentText.value.trim()
  if (!body || !video.value || postingComment.value) return
  postingComment.value = true
  const { data, error: apiError } = await api.POST(
    '/api/videos/{video_id}/comments/',
    {
      params: { path: { video_id: video.value.id } },
      body: { body },
    },
  )
  postingComment.value = false
  if (apiError || !data) {
    toast.push('Не удалось отправить комментарий')
    return
  }
  commentText.value = ''
  commentFocused.value = false
  comments.value = [data, ...comments.value]
}

function cancelComment() {
  commentText.value = ''
  commentFocused.value = false
}

function canDelete(_comment: CommentOut): boolean {
  // Authors can no longer delete their comments; only moderators/admins can.
  const role = auth.user?.role
  return role === 'moderator' || role === 'admin'
}

async function deleteComment(comment: CommentOut) {
  if (!video.value || !canDelete(comment)) return
  const { error: apiError } = await api.DELETE(
    '/api/videos/{video_id}/comments/{comment_id}',
    {
      params: {
        path: { video_id: video.value.id, comment_id: comment.id },
      },
    },
  )
  if (!apiError) {
    comments.value = comments.value.filter((c) => c.id !== comment.id)
  } else {
    toast.push('Не удалось удалить комментарий')
  }
}

function goToLogin() {
  router.push({ name: 'login', query: { next: route.fullPath } })
}

onMounted(load)
watch(
  () => route.params.id,
  () => {
    if (route.name === 'watch' && route.params.id) load()
  },
)
</script>

<template>
  <div class="page watch">
    <div v-if="error" class="error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="load">Повторить</button>
    </div>

    <div v-if="loading" class="loading watch-layout">
      <div class="watch-main">
        <div class="skeleton player-skeleton"></div>
        <div class="skeleton line-skeleton"></div>
        <div class="skeleton line-skeleton short"></div>
      </div>
      <div class="watch-side">
        <div v-for="n in 4" :key="n" class="related-skeleton">
          <div class="skeleton related-thumb-skeleton"></div>
          <div class="related-skeleton-lines">
            <div class="skeleton line-skeleton"></div>
            <div class="skeleton line-skeleton short"></div>
          </div>
        </div>
      </div>
    </div>

    <template v-else-if="video">
      <div class="watch-layout">
        <div class="watch-main">
          <!-- Still processing / failed -->
          <div v-if="video.status !== 'ready'" class="placeholder">
            <template v-if="video.status === 'failed'">
              <h2>Не удалось обработать видео</h2>
              <p>При обработке видео произошла ошибка.</p>
            </template>
            <template v-else>
              <h2>{{ video.status === 'processing' ? 'Обработка…' : 'Загрузка…' }}</h2>
              <p>Видео ещё не готово. Зайдите позже.</p>
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
            Ваш браузер не поддерживает воспроизведение видео.
          </video>

          <h1 class="title">{{ video.title }}</h1>

          <!-- Owner row: avatar + name + subs, subscribe pill on the right -->
          <div class="owner-row">
            <RouterLink
              v-if="video.owner"
              :to="{ name: 'channel', params: { id: video.owner.id } }"
              class="owner"
            >
              <span class="avatar avatar-40">
                {{ (video.owner.username || '?').charAt(0).toUpperCase() }}
              </span>
              <span class="owner-text">
                <span class="owner-name">{{ video.owner.username }}</span>
                <span v-if="channel" class="owner-subs">
                  {{ formatSubscribers(channel.subscriber_count) }}
                </span>
              </span>
            </RouterLink>
            <span v-else class="owner">
              <span class="avatar avatar-40">?</span>
            </span>

            <button
              v-if="canSubscribe"
              class="pill subscribe-pill"
              :class="{ subscribed: channel?.is_subscribed }"
              :disabled="subscribePending"
              @click="toggleSubscribe"
            >
              {{ channel?.is_subscribed ? 'Вы подписаны' : 'Подписаться' }}
            </button>
          </div>

          <!-- Actions row: like / dislike pills, report -->
          <div class="actions-row">
            <button
              class="pill like-pill"
              :class="{ active: likeStatus === 'like' }"
              :disabled="!auth.user || likePending"
              :title="auth.user ? undefined : 'Войдите, чтобы оценить'"
              @click="toggleLike"
            >
              <ThumbsUp :size="20" />
              <span>{{ likeCount }}</span>
            </button>
            <button
              class="pill like-pill"
              :class="{ active: likeStatus === 'dislike' }"
              :disabled="!auth.user || likePending"
              :title="auth.user ? undefined : 'Войдите, чтобы оценить'"
              @click="toggleDislike"
            >
              <ThumbsDown :size="20" />
              <span>{{ dislikeCount }}</span>
            </button>

            <span class="spacer"></span>

            <!-- Report -->
            <div v-if="!isOwner" class="report-area">
              <p v-if="reportDone" class="report-done">Жалоба отправлена. Спасибо.</p>
              <button v-else class="pill like-pill" @click="reportOpen = !reportOpen">
                <Flag :size="20" />
                <span>Пожаловаться</span>
              </button>
              <form v-if="reportOpen" class="report-form" @submit.prevent="submitReport">
                <textarea
                  v-model="reportReason"
                  placeholder="Причина жалобы"
                  rows="2"
                ></textarea>
                <div class="report-actions">
                  <button type="button" class="pill" @click="cancelReport">Отмена</button>
                  <button type="submit" class="pill pill-accent" :disabled="reportSending || !reportReason.trim()">
                    {{ reportSending ? 'Отправка…' : 'Отправить' }}
                  </button>
                </div>
              </form>
            </div>
          </div>

          <!-- Description box -->
          <div class="description" :class="{ collapsed: !descExpanded }">
            <div class="desc-meta">
              {{ formatViews(video.views) }} • {{ timeAgo(video.created_at) }}
            </div>
            <p v-if="video.description" class="desc-text">{{ video.description }}</p>
            <button
              v-if="video.description"
              type="button"
              class="desc-toggle"
              @click="descExpanded = !descExpanded"
            >
              {{ descExpanded ? 'Свернуть' : 'ещё' }}
            </button>
          </div>

          <!-- Comments -->
          <section class="comments">
            <h2 class="comments-title">{{ commentCountLabel }}</h2>

            <div v-if="auth.user" class="comment-form">
              <span class="avatar avatar-40">
                {{ (auth.user.username || '?').charAt(0).toUpperCase() }}
              </span>
              <div class="comment-form-body">
                <textarea
                  v-model="commentText"
                  class="comment-input"
                  rows="1"
                  placeholder="Введите комментарий…"
                  @focus="commentFocused = true"
                ></textarea>
                <div v-if="showCommentActions" class="comment-form-actions">
                  <button type="button" class="pill" @click="cancelComment">Отмена</button>
                  <button
                    type="button"
                    class="pill pill-accent"
                    :disabled="postingComment || !commentText.trim()"
                    @click="postComment"
                  >
                    {{ postingComment ? 'Отправка…' : 'Комментировать' }}
                  </button>
                </div>
              </div>
            </div>
            <p v-else class="signin-hint">
              <button class="link-btn" @click="goToLogin">Войдите</button>, чтобы комментировать.
            </p>

            <div v-if="commentsLoading && !comments.length" class="comment-skeletons">
              <div v-for="n in 3" :key="n" class="comment-skeleton">
                <div class="skeleton avatar-skeleton"></div>
                <div class="comment-skeleton-lines">
                  <div class="skeleton line-skeleton short"></div>
                  <div class="skeleton line-skeleton"></div>
                </div>
              </div>
            </div>

            <ul v-else-if="comments.length" class="comment-list">
              <li v-for="c in comments" :key="c.id" class="comment">
                <RouterLink
                  v-if="c.author"
                  :to="{ name: 'channel', params: { id: c.author.id } }"
                >
                  <span class="avatar avatar-40">
                    {{ (c.author.username || '?').charAt(0).toUpperCase() }}
                  </span>
                </RouterLink>
                <span v-else class="avatar avatar-40">?</span>
                <div class="comment-body">
                  <div class="comment-head">
                    <RouterLink
                      v-if="c.author"
                      :to="{ name: 'channel', params: { id: c.author.id } }"
                      class="comment-author"
                    >
                      {{ c.author.username }}
                    </RouterLink>
                    <span v-else class="comment-author">Неизвестный</span>
                    <span class="comment-age">{{ timeAgo(c.created_at) }}</span>
                    <button
                      v-if="canDelete(c)"
                      class="link-btn comment-delete"
                      @click="deleteComment(c)"
                    >
                      Удалить
                    </button>
                  </div>
                  <p class="comment-text">{{ c.body }}</p>
                </div>
              </li>
            </ul>

            <p v-else-if="!commentsLoading" class="no-comments">Комментариев пока нет.</p>

            <button
              v-if="commentsPage < commentsPages"
              class="pill show-more"
              :disabled="commentsLoading"
              @click="showMoreComments"
            >
              {{ commentsLoading ? 'Загрузка…' : 'Показать ещё' }}
            </button>
          </section>
        </div>

        <!-- Recommendations column: compact rows -->
        <aside class="watch-side">
          <h2 class="side-title">Похожие видео</h2>
          <RouterLink
            v-for="v in related"
            :key="v.id"
            :to="{ name: 'watch', params: { id: v.id } }"
            class="related-row"
          >
            <span class="related-thumb-wrap">
              <img
                class="related-thumb"
                :src="`/api/videos/${v.id}/poster`"
                alt=""
                loading="lazy"
              />
              <span v-if="v.duration_seconds" class="related-duration">
                {{ formatDuration(v.duration_seconds) }}
              </span>
            </span>
            <span class="related-info">
              <span class="related-title">{{ v.title }}</span>
              <span class="related-meta">
                {{ formatViews(v.views) }} • {{ timeAgo(v.created_at) }}
              </span>
            </span>
          </RouterLink>
          <p v-if="!related.length" class="no-related">Похожих видео нет.</p>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.watch {
  max-width: 1750px;
}

.watch-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 402px;
  gap: 24px;
  align-items: start;
}

@media (max-width: 1015px) {
  .watch-layout {
    grid-template-columns: 1fr;
  }
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
  background: var(--surface);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-2);
  text-align: center;
  padding: 16px;
}

.placeholder h2 {
  color: var(--text);
}

.title {
  font-size: 20px;
  line-height: 28px;
  font-weight: 700;
  margin: 12px 0 0;
}

/* ---- Avatar ---- */
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
  text-decoration: none;
}

.avatar-40 {
  width: 40px;
  height: 40px;
  font-size: 17px;
}

/* ---- Pills (subscribe, like, misc) ---- */
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

/* Subscribe: inverted (bg text / text bg) */
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

.like-pill {
  background: var(--surface);
  color: var(--text);
}

.like-pill:hover {
  background: var(--surface-hover);
}

.like-pill.active {
  background: var(--surface-hover);
}

.pill-accent {
  background: var(--accent);
  color: var(--bg);
}

.pill-accent:hover {
  background: var(--accent);
  opacity: 0.9;
}

/* ---- Owner row ---- */
.owner-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.owner {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text);
  text-decoration: none;
  min-width: 0;
}

.owner-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.owner-name {
  font-size: 16px;
  font-weight: 500;
  line-height: 22px;
}

.owner-subs {
  color: var(--text-2);
  font-size: 12px;
  line-height: 18px;
}

/* ---- Actions row ---- */
.actions-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.spacer {
  flex: 1;
}

/* ---- Report ---- */
.report-area {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.report-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 220px;
}

.report-form textarea {
  background: var(--bg);
  border: 1px solid var(--divider);
  color: var(--text);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
  font-size: 13px;
  resize: vertical;
}

.report-actions {
  display: flex;
  gap: 8px;
}

.report-done {
  margin: 0;
  color: var(--text-2);
  font-size: 12px;
}

/* ---- Description ---- */
.description {
  margin-top: 12px;
  padding: 12px;
  background: var(--surface);
  border-radius: 12px;
}

.desc-meta {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.desc-text {
  margin: 4px 0 0;
  font-size: 14px;
  line-height: 20px;
  color: var(--text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.description.collapsed .desc-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.desc-toggle {
  margin-top: 4px;
  padding: 0;
  background: none;
  border: none;
  color: var(--accent);
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

/* ---- Comments ---- */
.comments {
  margin-top: 24px;
}

.comments-title {
  font-size: 20px;
  line-height: 28px;
  font-weight: 700;
  margin: 0 0 16px;
}

.signin-hint {
  color: var(--text-2);
  font-size: 14px;
}

.link-btn {
  background: none;
  border: none;
  padding: 0;
  color: var(--accent);
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.link-btn:hover {
  opacity: 0.9;
}

.comment-form {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.comment-form-body {
  flex: 1;
  min-width: 0;
}

.comment-input {
  display: block;
  width: 100%;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--divider);
  color: var(--text);
  font: inherit;
  font-size: 14px;
  line-height: 20px;
  padding: 4px 0 8px;
  resize: vertical;
  min-height: 24px;
  outline: none;
}

.comment-input:focus {
  border-bottom-color: var(--accent);
}

.comment-input::placeholder {
  color: var(--text-2);
}

.comment-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.comment-list {
  list-style: none;
  padding: 0;
  margin: 24px 0 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment {
  display: flex;
  gap: 12px;
}

.comment-body {
  flex: 1;
  min-width: 0;
}

.comment-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.comment-author {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  text-decoration: none;
}

.comment-age {
  font-size: 12px;
  color: var(--text-2);
}

.comment-delete {
  color: var(--text-2);
  font-size: 12px;
  font-weight: 400;
}

.comment-delete:hover {
  color: var(--text);
}

.comment-text {
  margin: 2px 0 0;
  font-size: 14px;
  line-height: 20px;
  color: var(--text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.no-comments {
  margin: 24px 0 0;
  color: var(--text-2);
  font-size: 14px;
}

.show-more {
  margin-top: 16px;
}

/* ---- Right column ---- */
.watch-side {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.side-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
  margin: 0 0 8px;
}

.related-row {
  display: flex;
  gap: 8px;
  color: var(--text);
  text-decoration: none;
}

.related-thumb-wrap {
  position: relative;
  width: 168px;
  height: 94px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
}

.related-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.related-duration {
  position: absolute;
  right: 4px;
  bottom: 4px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  line-height: 14px;
  border-radius: 4px;
  padding: 1px 4px;
}

.related-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.related-title {
  font-size: 14px;
  font-weight: 500;
  line-height: 20px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.related-meta {
  font-size: 12px;
  color: var(--text-2);
}

.no-related {
  color: var(--text-2);
  font-size: 13px;
}

/* Skeleton extras */
.related-skeleton {
  display: flex;
  gap: 8px;
}

.related-thumb-skeleton {
  width: 168px;
  height: 94px;
  border-radius: 8px;
  flex-shrink: 0;
}

.related-skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 4px;
}

.related-skeleton-lines .line-skeleton {
  margin-top: 0;
}

.avatar-skeleton {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex-shrink: 0;
}

.comment-skeletons {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 24px;
}

.comment-skeleton {
  display: flex;
  gap: 12px;
}

.comment-skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
