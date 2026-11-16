<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'
import { useAuthStore } from '../stores/auth'
import VideoCard from '../components/VideoCard.vue'
import { formatViews, timeAgo } from '../utils/format'

type VideoOut = components['schemas']['VideoOut']
type ChannelOut = components['schemas']['ChannelOut']
type CommentOut = components['schemas']['CommentOut']
type LikeInfo = components['schemas']['LikeInfo']

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

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
const commentError = ref('')

// ---- Like state (optimistic) ----
const likePending = ref(false)
const myLike = ref<boolean | null>(null) // true = liked, false/null = not liked
const likeCount = ref(0)
const dislikeCount = ref(0)

const videoId = computed(() => String(route.params.id))
const isOwner = computed(
  () => !!video.value && !!auth.user && auth.user.id === video.value.owner_id,
)
const canSubscribe = computed(
  () => !!auth.user && !!channel.value && !isOwner.value,
)

// ---- Report (owner never sees the button) ----
const reportOpen = ref(false)
const reportDone = ref(false)
const reportReason = ref('')
const reportSending = ref(false)
const reportError = ref('')

function cancelReport() {
  reportOpen.value = false
  reportReason.value = ''
  reportError.value = ''
}

async function submitReport() {
  if (!video.value || !reportReason.value.trim() || reportSending.value) return
  reportSending.value = true
  reportError.value = ''
  const { error: apiError } = await api.POST('/api/reports/', {
    body: { video_id: video.value.id, reason: reportReason.value.trim() },
  })
  reportSending.value = false
  if (apiError) {
    reportError.value = extractError(apiError, 'Failed to send report')
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
    error.value = 'Video not found or unavailable.'
    video.value = null
    loading.value = false
    return
  }
  video.value = data
  myLike.value = data.user_like ?? null
  likeCount.value = data.like_count
  dislikeCount.value = data.dislike_count
  loading.value = false

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

// ---- Like toggle ----
/**
 * Optimistically apply a vote transition, then reconcile `user_like` with the
 * returned LikeInfo. If the server disagrees with our optimistic guess, the
 * counts may be stale — refetch the video to resync.
 */
async function toggleLike() {
  if (!auth.user || !video.value || likePending.value) return
  likePending.value = true
  const id = video.value.id
  const wasLiked = myLike.value === true

  // Optimistic counts.
  if (wasLiked) {
    likeCount.value = Math.max(0, likeCount.value - 1)
    myLike.value = null
  } else {
    if (myLike.value === false) {
      dislikeCount.value = Math.max(0, dislikeCount.value - 1)
    }
    likeCount.value += 1
    myLike.value = true
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
    await resyncVideo(id)
    return
  }
  syncFromLikeInfo(data, wasLiked, id)
}

function syncFromLikeInfo(info: LikeInfo, wasLiked: boolean, id: string) {
  const serverLiked = info.liked === true
  myLike.value = serverLiked ? true : null
  // The LikeInfo payload carries no counts; if our optimistic guess matched
  // the server transition they are already right, otherwise resync.
  if (serverLiked === wasLiked) {
    void resyncVideo(id)
  }
}

async function resyncVideo(id: string) {
  const { data } = await api.GET('/api/videos/{video_id}', {
    params: { path: { video_id: id } },
  })
  if (data) {
    video.value = data
    myLike.value = data.user_like ?? null
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
  commentError.value = ''
  const { data, error: apiError } = await api.POST(
    '/api/videos/{video_id}/comments/',
    {
      params: { path: { video_id: video.value.id } },
      body: { body },
    },
  )
  postingComment.value = false
  if (apiError || !data) {
    commentError.value = 'Failed to post comment.'
    return
  }
  commentText.value = ''
  comments.value = [data, ...comments.value]
}

function canDelete(comment: CommentOut): boolean {
  return !!auth.user && comment.author_id === auth.user.id
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
      <button class="btn retry-btn" @click="load">Retry</button>
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
          <div class="skeleton line-skeleton"></div>
        </div>
      </div>
    </div>

    <template v-else-if="video">
      <div class="watch-layout">
        <div class="watch-main">
          <!-- Still processing / failed -->
          <div v-if="video.status !== 'ready'" class="placeholder">
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

          <div class="action-row">
            <RouterLink
              v-if="video.owner"
              :to="{ name: 'channel', params: { id: video.owner.id } }"
              class="owner"
            >
              <span class="avatar avatar-small">
                {{ (video.owner.username || '?').charAt(0).toUpperCase() }}
              </span>
              <span class="owner-name">
                {{ video.owner.username }}
                <span class="owner-sub">{{ formatViews(video.views) }} • {{ timeAgo(video.created_at) }}</span>
              </span>
            </RouterLink>

            <button
              v-if="canSubscribe"
              class="btn subscribe-btn"
              :class="{ subscribed: channel?.is_subscribed }"
              :disabled="subscribePending"
              @click="toggleSubscribe"
            >
              {{ channel?.is_subscribed ? 'Subscribed' : 'Subscribe' }}
            </button>

            <div class="spacer"></div>

            <div class="vote-group">
              <button
                class="btn vote-btn"
                :class="{ active: myLike === true }"
                :disabled="!auth.user || likePending"
                :title="auth.user ? undefined : 'Sign in to like'"
                @click="toggleLike"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M1 21h4V9H1v12zM23 10c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.72v-2z" />
                </svg>
                {{ likeCount }}
              </button>
              <button
                class="btn vote-btn"
                :class="{ active: myLike === false }"
                :disabled="!auth.user || likePending || myLike !== true"
                :title="!auth.user ? 'Sign in to rate' : myLike === true ? 'Remove your like' : 'Ratings are like-only'"
                @click="myLike === true && toggleLike()"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.72v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z" />
                </svg>
                {{ dislikeCount }}
              </button>
            </div>

            <!-- Report (hidden from the video owner) -->
            <div v-if="auth.user && !isOwner" class="report-area">
              <button
                v-if="!reportOpen && !reportDone"
                class="btn"
                title="Report this video"
                @click="reportOpen = true"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14.4 6L14 4H5v17h2v-7h5.6l.4 2h7V6z" />
                </svg>
                Report
              </button>
              <form v-if="reportOpen" class="report-form" @submit.prevent="submitReport">
                <textarea
                  v-model="reportReason"
                  rows="2"
                  placeholder="Why are you reporting this video?"
                ></textarea>
                <div class="report-actions">
                  <button
                    class="btn btn-primary"
                    type="submit"
                    :disabled="reportSending || !reportReason.trim()"
                  >
                    {{ reportSending ? 'Sending…' : 'Send report' }}
                  </button>
                  <button class="btn" type="button" @click="cancelReport">Cancel</button>
                </div>
                <p v-if="reportError" class="report-error">{{ reportError }}</p>
              </form>
              <p v-if="reportDone" class="report-done">Report sent. Thank you.</p>
            </div>
          </div>

          <div v-if="video.description" class="description">{{ video.description }}</div>

          <!-- Comments -->
          <section class="comments">
            <h2 class="comments-title">
              {{ video.comment_count }} {{ video.comment_count === 1 ? 'Comment' : 'Comments' }}
            </h2>

            <div v-if="auth.user" class="comment-form">
              <span class="avatar avatar-small">
                {{ (auth.user.username || '?').charAt(0).toUpperCase() }}
              </span>
              <div class="comment-form-body">
                <textarea
                  v-model="commentText"
                  class="input"
                  rows="2"
                  placeholder="Add a comment…"
                  @keydown.ctrl.enter="postComment"
                  @keydown.meta.enter="postComment"
                ></textarea>
                <div v-if="commentError" class="comment-error">{{ commentError }}</div>
                <div class="comment-form-actions">
                  <button
                    class="btn"
                    :disabled="postingComment || !commentText.trim()"
                    @click="postComment"
                  >
                    Comment
                  </button>
                </div>
              </div>
            </div>
            <p v-else class="signin-hint">
              <button class="link-btn" @click="goToLogin">Sign in</button> to comment.
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
                <span class="avatar avatar-small">
                  {{ (c.author?.username || '?').charAt(0).toUpperCase() }}
                </span>
                <div class="comment-body">
                  <div class="comment-head">
                    <RouterLink
                      v-if="c.author"
                      :to="{ name: 'channel', params: { id: c.author.id } }"
                      class="comment-author"
                    >
                      {{ c.author.username }}
                    </RouterLink>
                    <span v-else class="comment-author">Unknown</span>
                    <span class="comment-age">{{ timeAgo(c.created_at) }}</span>
                    <button
                      v-if="canDelete(c)"
                      class="link-btn comment-delete"
                      @click="deleteComment(c)"
                    >
                      Delete
                    </button>
                  </div>
                  <p class="comment-text">{{ c.body }}</p>
                </div>
              </li>
            </ul>

            <p v-else-if="!commentsLoading" class="no-comments">No comments yet.</p>

            <button
              v-if="commentsPage < commentsPages"
              class="btn show-more"
              :disabled="commentsLoading"
              @click="showMoreComments"
            >
              {{ commentsLoading ? 'Loading…' : 'Show more' }}
            </button>
          </section>
        </div>

        <!-- Recommendations column -->
        <aside class="watch-side">
          <h2 class="side-title">Up next</h2>
          <VideoCard v-for="v in related" :key="v.id" :video="v" class="related-card" />
          <p v-if="!related.length" class="no-related">No related videos.</p>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.watch {
  max-width: 1400px;
}

.watch-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 24px;
  align-items: start;
}

@media (max-width: 1000px) {
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

/* ---- Action row ---- */
.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}

/* ---- Report ---- */
.report-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.report-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 220px;
}

.report-form textarea {
  background: var(--input-bg);
  border: 1px solid var(--border);
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

.report-error {
  margin: 0;
  color: var(--danger);
  font-size: 12px;
}

.report-done {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.owner {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text);
}

.owner-name {
  display: flex;
  flex-direction: column;
  font-weight: 600;
  font-size: 14px;
}

.owner-sub {
  color: var(--text-secondary);
  font-weight: 400;
  font-size: 12px;
}

.subscribe-btn.subscribed {
  background: var(--bg-elevated);
  color: var(--text-secondary);
}

.spacer {
  flex: 1;
}

.vote-group {
  display: flex;
  gap: 0;
}

.vote-btn {
  border-radius: 18px 0 0 18px;
}

.vote-btn + .vote-btn {
  border-radius: 0 18px 18px 0;
  border-left: 1px solid var(--border);
}

.vote-btn.active {
  background: var(--bg-hover);
  color: var(--accent);
}

.description {
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--bg-elevated);
  border-radius: 12px;
  white-space: pre-wrap;
}

/* ---- Comments ---- */
.comments {
  margin-top: 24px;
}

.comments-title {
  font-size: 16px;
  margin-bottom: 16px;
}

.comment-form {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.comment-form-body {
  flex: 1;
}

.comment-form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.comment-error {
  color: var(--danger);
  font-size: 13px;
  margin-top: 6px;
}

.signin-hint {
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.link-btn {
  background: none;
  border: none;
  padding: 0;
  color: var(--accent);
  cursor: pointer;
  font: inherit;
}

.link-btn:hover {
  text-decoration: underline;
}

.comment-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
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
  font-weight: 600;
  font-size: 13px;
  color: var(--text);
}

.comment-age {
  color: var(--text-secondary);
  font-size: 12px;
}

.comment-delete {
  font-size: 12px;
  color: var(--text-secondary);
  margin-left: auto;
}

.comment-delete:hover {
  color: var(--danger);
}

.comment-text {
  margin: 4px 0 0;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.no-comments {
  color: var(--text-secondary);
}

.show-more {
  margin-top: 16px;
}

/* ---- Avatars ---- */
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

.avatar-small {
  width: 36px;
  height: 36px;
  font-size: 15px;
}

/* ---- Recommendations ---- */
.watch-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.side-title {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.related-thumb-skeleton {
  aspect-ratio: 16 / 9;
}

.related-skeleton .line-skeleton {
  margin-top: 8px;
}

.no-related {
  color: var(--text-secondary);
  font-size: 13px;
}

/* Skeleton extras */
.avatar-skeleton {
  width: 36px;
  height: 36px;
  border-radius: 50%;
}

.comment-skeletons {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
