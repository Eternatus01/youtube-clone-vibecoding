<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Check, ShieldCheck } from 'lucide-vue-next'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'
import { timeAgo } from '../utils/format'
import { useToast } from '../composables/useToast'

type ReportOut = components['schemas']['ReportOut']
type ModerationActionOut = components['schemas']['ModerationActionOut']

type Tab = 'reports' | 'actions'

const toast = useToast()

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
    error.value = extractError(err, 'Не удалось загрузить')
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
    error.value = extractError(err, 'Не удалось загрузить')
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
    toast.push('Укажите причину решения')
    return
  }
  resolving.value[report.id] = true
  const { error: err } = await api.POST('/api/moderation/resolve', {
    body: {
      video_id: report.video_id,
      action,
      reason,
    },
  })
  resolving.value[report.id] = false
  if (err) {
    toast.push(extractError(err, 'Не удалось разрешить жалобу'))
    return
  }
  reports.value = reports.value.filter((r) => r.id !== report.id)
  resolveReason.value[report.id] = ''
  toast.push('Жалоба разрешена')
}

const actionLabel: Record<string, string> = {
  hide: 'Скрыто',
  restore: 'Восстановлено',
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
    <h1 class="page-title">Модерация</h1>

    <div class="tabs">
      <button
        class="tab"
        :class="{ active: tab === 'reports' }"
        @click="switchTab('reports')"
      >
        Жалобы
        <span v-if="openCount > 0 && tab !== 'reports'" class="count">{{ openCount }}</span>
      </button>
      <button
        class="tab"
        :class="{ active: tab === 'actions' }"
        @click="switchTab('actions')"
      >
        Действия
      </button>
    </div>

    <div v-if="error" class="load-error">
      <span>{{ error }}</span>
      <button class="retry" type="button" @click="retry">Повторить</button>
    </div>

    <div v-if="loading" class="table-skeleton">
      <div v-for="n in 5" :key="n" class="skel-row">
        <div class="line-skeleton" :class="n % 2 === 0 ? 'w40' : 'w60'"></div>
        <div class="line-skeleton w30"></div>
      </div>
    </div>

    <!-- Жалобы -->
    <template v-else-if="tab === 'reports'">
      <table v-if="reports.length > 0" class="table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Автор</th>
            <th>Видео</th>
            <th>Причина</th>
            <th>Действие</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in reports" :key="r.id">
            <td class="cell-date">{{ timeAgo(r.created_at) }}</td>
            <td class="cell-user">{{ r.reporter?.username ?? r.reporter_id }}</td>
            <td class="cell-video">
              <RouterLink
                class="video-link"
                :to="{ name: 'watch', params: { id: r.video_id } }"
              >
                {{ r.video?.title ?? r.video_id }}
              </RouterLink>
            </td>
            <td class="cell-reason" :title="r.reason">{{ r.reason }}</td>
            <td>
              <div class="resolve-cell">
                <select
                  v-model="resolveAction[r.id]"
                  class="small-select"
                  aria-label="Действие"
                >
                  <option value="hide">Скрыть</option>
                  <option value="restore">Восстановить</option>
                </select>
                <input
                  v-model="resolveReason[r.id]"
                  class="small-input"
                  type="text"
                  placeholder="Причина"
                  aria-label="Причина решения"
                />
                <button
                  class="icon-btn"
                  type="button"
                  title="Разрешить"
                  :disabled="resolving[r.id]"
                  @click="resolve(r, resolveAction[r.id] ?? 'hide')"
                >
                  <Check :size="18" :stroke-width="1.75" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-else-if="!error" class="empty">
        <ShieldCheck :size="48" :stroke-width="1.75" class="empty-icon" />
        <p>Нет открытых жалоб</p>
      </div>
    </template>

    <!-- Действия -->
    <template v-else>
      <table v-if="actions.length > 0" class="table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Модератор</th>
            <th>Видео</th>
            <th>Решение</th>
            <th>Причина</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in actions" :key="a.id">
            <td class="cell-date">{{ formatDate(a.created_at) }}</td>
            <td class="cell-user">{{ a.moderator?.username ?? a.moderator_id }}</td>
            <td class="cell-video">
              <RouterLink class="video-link video-link--id" :to="`/watch/${a.video_id}`">
                {{ a.video_id }}
              </RouterLink>
            </td>
            <td>
              <span class="pill" :class="a.action">{{ actionLabel[a.action] ?? a.action }}</span>
            </td>
            <td class="cell-reason" :title="a.reason || '—'">{{ a.reason || '—' }}</td>
          </tr>
        </tbody>
      </table>

      <div v-else-if="!error" class="empty">
        <ShieldCheck :size="48" :stroke-width="1.75" class="empty-icon" />
        <p>Нет действий модерации</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 980px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

.page-title {
  font-size: 20px;
  font-weight: 500;
  margin: 0 0 4px;
}

/* ---- Tabs ---- */
.tabs {
  display: flex;
  gap: 24px;
  border-bottom: 1px solid var(--divider);
  margin: 20px 0 0;
}

.tab {
  padding: 0 0;
  height: 40px;
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

.count {
  margin-left: 6px;
  font-size: 12px;
  color: var(--text-2);
}

/* ---- Load error ---- */
.load-error {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
  font-size: 13px;
  color: var(--danger);
}

.retry {
  background: none;
  border: 1px solid var(--divider);
  color: var(--text);
  padding: 4px 14px;
  border-radius: 16px;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.retry:hover {
  background: var(--surface-hover);
}

/* ---- Dense table ---- */
.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}

.table th {
  position: sticky;
  top: var(--topbar-h);
  z-index: 5;
  background: var(--bg);
  height: 36px;
  padding: 0 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  text-transform: none;
  color: var(--text-2);
  border-bottom: 1px solid var(--divider);
  white-space: nowrap;
}

.table td {
  height: 48px;
  padding: 4px 12px;
  border-bottom: 1px solid var(--divider);
  font-size: 13px;
  color: var(--text);
  vertical-align: middle;
}

.cell-date {
  color: var(--text-2);
  white-space: nowrap;
}

.cell-user {
  color: var(--text-2);
  white-space: nowrap;
}

.cell-video {
  max-width: 360px;
}

.video-link {
  color: var(--text);
  text-decoration: none;
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.video-link:hover {
  text-decoration: underline;
}

.video-link--id {
  font-size: 12px;
  color: var(--text-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
  display: block;
}

.cell-reason {
  max-width: 300px;
  color: var(--text-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- Resolve controls ---- */
.resolve-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 300px;
}

.small-select,
.small-input {
  background: var(--bg);
  border: 1px solid var(--divider);
  color: var(--text);
  border-radius: 8px;
  padding: 4px 8px;
  font: inherit;
  font-size: 13px;
}

.small-input {
  width: 120px;
}

.icon-btn {
  width: 32px;
  height: 32px;
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 50%;
  color: var(--text-2);
  cursor: pointer;
}

.icon-btn:hover:not(:disabled) {
  background: var(--surface-hover);
  color: var(--text);
}

.icon-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

/* ---- Status pill ---- */
.pill {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid var(--divider);
  color: var(--text-2);
  background: transparent;
  white-space: nowrap;
}

.pill.hide {
  color: var(--danger);
  border-color: var(--danger);
}

.pill.restore {
  color: #2e7d32;
  border-color: #2e7d32;
}

/* ---- States ---- */
.table-skeleton {
  margin-top: 8px;
}

.skel-row {
  height: 48px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid var(--divider);
}

.line-skeleton {
  height: 12px;
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

.w60 { width: 60%; }
.w40 { width: 40%; }
.w30 { width: 30%; }

@keyframes shimmer {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}

.empty {
  padding: 40px 16px;
  text-align: center;
  color: var(--text-2);
  font-size: 14px;
}

.empty-icon {
  display: block;
  margin: 0 auto 12px;
  color: var(--text-2);
}
</style>
