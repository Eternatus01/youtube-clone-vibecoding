<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'
import { timeAgo } from '../utils/format'

type ReportOut = components['schemas']['ReportOut']
type ModerationActionOut = components['schemas']['ModerationActionOut']

type Tab = 'reports' | 'actions'

const tab = ref<Tab>('reports')

const reports = ref<ReportOut[]>([])
const actions = ref<ModerationActionOut[]>([])
const loading = ref(true)
const error = ref('')

// Per-report resolve form state.
const resolving = ref<Record<string, boolean>>({})
const resolveAction = ref<Record<string, 'hide' | 'restore'>>({})
const resolveReason = ref<Record<string, string>>({})

const openCount = computed(() => reports.value.length)

async function loadReports() {
  loading.value = true
  error.value = ''
  const { data, error: err } = await api.GET('/api/moderation/reports', {
    params: { query: { status_filter: 'open', page: 1, page_size: 50 } },
  })
  if (err || !data) {
    error.value = extractError(err, 'Failed to load reports')
    reports.value = []
  } else {
    reports.value = data.items as ReportOut[]
    for (const r of reports.value) {
      resolveAction.value[r.id] = 'hide'
    }
  }
  loading.value = false
}

async function loadActions() {
  loading.value = true
  error.value = ''
  const { data, error: err } = await api.GET('/api/moderation/actions', {
    params: { query: { page: 1, page_size: 50 } },
  })
  if (err || !data) {
    error.value = extractError(err, 'Failed to load actions')
    actions.value = []
  } else {
    actions.value = data.items as ModerationActionOut[]
  }
  loading.value = false
}

function switchTab(t: Tab) {
  tab.value = t
  if (t === 'reports') loadReports()
  else loadActions()
}

function retry() {
  if (tab.value === 'reports') loadReports()
  else loadActions()
}

async function resolve(report: ReportOut, action: 'hide' | 'restore') {
  const reason = (resolveReason.value[report.id] ?? '').trim()
  if (!reason) {
    error.value = 'A reason is required to resolve a report.'
    return
  }
  resolving.value[report.id] = true
  error.value = ''
  const { error: err } = await api.POST('/api/moderation/resolve', {
    body: {
      video_id: report.video_id,
      action,
      reason,
    },
  })
  resolving.value[report.id] = false
  if (err) {
    error.value = extractError(err, 'Failed to resolve report')
    return
  }
  reports.value = reports.value.filter((r) => r.id !== report.id)
  resolveReason.value[report.id] = ''
}

const actionLabel: Record<string, string> = {
  hide: 'Hidden',
  restore: 'Restored',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(loadReports)
</script>

<template>
  <div class="page">
    <h1 class="page-title">Moderation</h1>

    <div class="tabs">
      <button
        class="tab"
        :class="{ active: tab === 'reports' }"
        @click="switchTab('reports')"
      >
        Open reports
        <span v-if="openCount > 0 && tab !== 'reports'" class="count">{{ openCount }}</span>
      </button>
      <button
        class="tab"
        :class="{ active: tab === 'actions' }"
        @click="switchTab('actions')"
      >
        Actions
      </button>
    </div>

    <div v-if="error" class="banner error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="retry">Retry</button>
    </div>

    <div v-if="loading" class="skeletons">
      <div v-for="n in 3" :key="n" class="card item-skeleton">
        <div class="line-skeleton w60"></div>
        <div class="line-skeleton w40"></div>
      </div>
    </div>

    <!-- Open reports -->
    <template v-else-if="tab === 'reports'">
      <div v-if="reports.length === 0" class="empty card">
        <p class="empty-title">No open reports.</p>
        <p class="empty-hint">Reports from users will appear here.</p>
      </div>
      <div v-else class="report-list">
        <div v-for="r in reports" :key="r.id" class="card report-card">
          <div class="report-head">
            <div class="report-main">
              <p class="report-reason">{{ r.reason }}</p>
              <p class="report-meta">
                <template v-if="r.video">
                  Video:
                  <RouterLink
                    :to="{ name: 'watch', params: { id: r.video.id } }"
                    class="video-link"
                  >{{ r.video.title }}</RouterLink>
                  ·
                </template>
                <template v-else>Video {{ r.video_id }} ·</template>
                Reported by {{ r.reporter?.username ?? r.reporter_id }} ·
                {{ timeAgo(r.created_at) }}
              </p>
            </div>
          </div>
          <div class="resolve-form">
            <select v-model="resolveAction[r.id]">
              <option value="hide">Hide video</option>
              <option value="restore">Restore video</option>
            </select>
            <input
              v-model="resolveReason[r.id]"
              type="text"
              placeholder="Reason for the action"
            />
            <button
              class="btn primary-btn"
              :disabled="resolving[r.id] || !(resolveReason[r.id] ?? '').trim()"
              @click="resolve(r, resolveAction[r.id] ?? 'hide')"
            >
              {{ resolving[r.id] ? 'Resolving…' : 'Resolve' }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- Actions log -->
    <template v-else>
      <div v-if="actions.length === 0" class="empty card">
        <p class="empty-title">No moderation actions yet.</p>
        <p class="empty-hint">Resolved reports will appear here.</p>
      </div>
      <div v-else class="report-list">
        <div v-for="a in actions" :key="a.id" class="card action-card">
          <p class="action-line">
            <span class="action-badge" :class="a.action">
              {{ actionLabel[a.action] ?? a.action }}
            </span>
            <template v-if="a.moderator">
              by {{ a.moderator.username }}
            </template>
            · {{ formatDate(a.created_at) }}
          </p>
          <p class="action-reason">Reason: {{ a.reason || '—' }}</p>
          <p class="report-meta">Video {{ a.video_id }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}

.tab {
  background: none;
  border: none;
  color: var(--text-secondary);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  padding: 10px 16px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab:hover {
  color: var(--text);
}

.tab.active {
  color: var(--text);
  border-bottom-color: var(--accent);
}

.count {
  background: var(--accent);
  color: #fff;
  font-size: 11px;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
}

.banner {
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
}

.error-banner {
  background: color-mix(in srgb, var(--danger) 12%, transparent);
  color: var(--danger);
  border: 1px solid var(--danger);
}

.card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 12px;
}

.skeletons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item-skeleton {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.line-skeleton {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(
    90deg,
    var(--skeleton) 25%,
    var(--skeleton-shine) 50%,
    var(--skeleton) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

.w60 { width: 60%; }
.w40 { width: 40%; }

@keyframes shimmer {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}

.empty {
  padding: 40px 16px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-title {
  color: var(--text);
  font-size: 16px;
  margin: 0 0 4px;
}

.empty-hint {
  margin: 0;
}

.report-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-card,
.action-card {
  padding: 14px 16px;
}

.report-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.report-main {
  min-width: 0;
}

.report-reason {
  margin: 0 0 4px;
  font-size: 14px;
  color: var(--text);
  word-break: break-word;
}

.report-meta {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.video-link {
  color: var(--text);
  text-decoration: none;
  font-weight: 600;
}

.video-link:hover {
  text-decoration: underline;
}

.resolve-form {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.resolve-form select,
.resolve-form input {
  background: var(--input-bg);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 7px 10px;
  font: inherit;
  font-size: 13px;
}

.resolve-form select {
  flex: 0 0 150px;
}

.resolve-form input {
  flex: 1;
  min-width: 180px;
}

.btn {
  background: var(--bg-elevated);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 6px 14px;
  border-radius: 18px;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.btn:hover:not(:disabled) {
  background: var(--bg-hover);
}

.primary-btn {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.primary-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.action-line {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.action-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.action-badge.hide {
  color: var(--danger);
  border-color: var(--danger);
}

.action-badge.restore {
  color: #2e7d32;
  border-color: #2e7d32;
}

.action-reason {
  margin: 0 0 2px;
  font-size: 13px;
  color: var(--text);
  word-break: break-word;
}
</style>
