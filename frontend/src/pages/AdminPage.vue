<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Ban } from 'lucide-vue-next'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'
import { pluralRu } from '../utils/format'
import { useToast } from '../composables/useToast'
import ConfirmDialog from '../components/ConfirmDialog.vue'

type UserOut = components['schemas']['UserOut']

const toast = useToast()

const users = ref<UserOut[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')

// Per-user UI state.
const busy = ref<Record<string, boolean>>({})
const roleSelect = ref<Record<string, string>>({})
const pendingDeactivate = ref<UserOut | null>(null)

const ROLES = ['user', 'moderator', 'admin'] as const

const roleLabel: Record<string, string> = {
  admin: 'админ',
  moderator: 'модератор',
  user: 'юзер',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const totalLabel = () =>
  pluralRu(total.value, ['пользователь', 'пользователя', 'пользователей'])

async function load() {
  loading.value = true
  error.value = ''
  const { data, error: err } = await api.GET('/api/admin/users')
  if (err || !data) {
    error.value = extractError(err, 'Не удалось загрузить')
    users.value = []
    total.value = 0
  } else {
    users.value = data.users
    total.value = data.total
    for (const u of data.users) {
      roleSelect.value[u.id] = u.role
    }
  }
  loading.value = false
}

async function changeRole(u: UserOut) {
  const role = roleSelect.value[u.id]
  if (!role || role === u.role) return
  busy.value[u.id] = true
  const { data, error: err } = await api.PATCH('/api/admin/users/role', {
    body: { user_id: u.id, role },
  })
  busy.value[u.id] = false
  if (err || !data) {
    toast.push(extractError(err, 'Не удалось изменить роль'))
    roleSelect.value[u.id] = u.role
    return
  }
  u.role = data.role
  toast.push(`Роль ${u.username}: ${roleLabel[data.role] ?? data.role}`)
}

async function deactivate(u: UserOut) {
  busy.value[u.id] = true
  const { error: err } = await api.DELETE('/api/admin/users/{user_id}', {
    params: { path: { user_id: u.id } },
  })
  busy.value[u.id] = false
  if (err) {
    toast.push(extractError(err, 'Не удалось деактивировать пользователя'))
    return
  }
  users.value = users.value.filter((row) => row.id !== u.id)
  total.value = Math.max(0, total.value - 1)
  toast.push(`Пользователь ${u.username} деактивирован`)
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1 class="page-title">Администрирование</h1>
    <p class="subtitle">{{ total }} {{ totalLabel() }}</p>

    <div v-if="error" class="load-error">
      <span>{{ error }}</span>
      <button class="retry" type="button" @click="load">Повторить</button>
    </div>

    <div v-if="loading" class="table-skeleton">
      <div v-for="n in 6" :key="n" class="skel-row">
        <div class="line-skeleton" :class="n % 2 === 0 ? 'w40' : 'w60'"></div>
        <div class="line-skeleton w30"></div>
      </div>
    </div>

    <table v-else-if="users.length > 0" class="table">
      <thead>
        <tr>
          <th>Пользователь</th>
          <th>Email</th>
          <th>Роль</th>
          <th>Дата</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>
            <span class="user-name">{{ u.username }}</span>
            <span class="role-pill" :class="`role-${u.role}`">
              {{ roleLabel[u.role] ?? u.role }}
            </span>
          </td>
          <td class="cell-email" :title="u.email">{{ u.email }}</td>
          <td>
            <select
              v-model="roleSelect[u.id]"
              class="role-select"
              :disabled="busy[u.id]"
              aria-label="Роль"
              @change="changeRole(u)"
            >
              <option v-for="r in ROLES" :key="r" :value="r">{{ roleLabel[r] ?? r }}</option>
            </select>
          </td>
          <td class="cell-date">{{ formatDate(u.created_at) }}</td>
          <td>
            <button
              class="icon-btn icon-btn--danger"
              type="button"
              title="Деактивировать"
              :disabled="busy[u.id]"
              @click="pendingDeactivate = u"
            >
              <Ban :size="18" :stroke-width="1.75" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else-if="!error" class="empty">Нет пользователей</div>

    <ConfirmDialog
      :open="pendingDeactivate !== null"
      title="Деактивировать пользователя?"
      :message="`Пользователь «${pendingDeactivate?.username ?? ''}» больше не сможет войти в аккаунт.`"
      confirm-text="Деактивировать"
      @confirm="deactivate(pendingDeactivate!); pendingDeactivate = null"
      @cancel="pendingDeactivate = null"
    />
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

.subtitle {
  margin: 0;
  font-size: 13px;
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
  margin-top: 24px;
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

.user-name {
  font-size: 14px;
  color: var(--text);
  margin-right: 8px;
}

/* ---- Role pill ---- */
.role-pill {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid var(--divider);
  color: var(--text-2);
  vertical-align: middle;
}

.role-pill.role-admin {
  color: var(--accent);
  border-color: var(--accent);
}

.role-pill.role-moderator {
  color: #2e7d32;
  border-color: #2e7d32;
}

.cell-email {
  max-width: 200px;
  color: var(--text-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-date {
  color: var(--text-2);
  white-space: nowrap;
}

.role-select {
  background: var(--bg);
  border: 1px solid var(--divider);
  color: var(--text);
  border-radius: 8px;
  padding: 4px 8px;
  font: inherit;
  font-size: 13px;
}

.role-select:disabled {
  opacity: 0.6;
  cursor: default;
}

/* ---- Icon button ---- */
.icon-btn {
  width: 32px;
  height: 32px;
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

.icon-btn--danger {
  color: var(--danger);
}

.icon-btn--danger:hover:not(:disabled) {
  color: var(--danger);
}

.icon-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

/* ---- States ---- */
.table-skeleton {
  margin-top: 24px;
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
</style>
