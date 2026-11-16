<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, extractError } from '../api/client'
import type { components } from '../api/schema'

type UserOut = components['schemas']['UserOut']

const users = ref<UserOut[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')
const message = ref('')

// Per-user UI state.
const busy = ref<Record<string, boolean>>({})
const roleSelect = ref<Record<string, string>>({})

const ROLES = ['user', 'moderator', 'admin'] as const

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

async function load() {
  loading.value = true
  error.value = ''
  const { data, error: err } = await api.GET('/api/admin/users')
  if (err || !data) {
    error.value = extractError(err, 'Failed to load users')
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
  error.value = ''
  message.value = ''
  const { data, error: err } = await api.PATCH('/api/admin/users/role', {
    body: { user_id: u.id, role },
  })
  busy.value[u.id] = false
  if (err || !data) {
    error.value = extractError(err, 'Failed to change role')
    roleSelect.value[u.id] = u.role
    return
  }
  u.role = data.role
  message.value = `Role of ${u.username} changed to ${data.role}`
}

async function deactivate(u: UserOut) {
  if (!confirm(`Deactivate "${u.username}"? They will no longer be able to sign in.`)) return
  busy.value[u.id] = true
  error.value = ''
  message.value = ''
  const { error: err } = await api.DELETE('/api/admin/users/{user_id}', {
    params: { path: { user_id: u.id } },
  })
  busy.value[u.id] = false
  if (err) {
    error.value = extractError(err, 'Failed to deactivate user')
    return
  }
  users.value = users.value.filter((row) => row.id !== u.id)
  total.value = Math.max(0, total.value - 1)
  message.value = `User ${u.username} deactivated`
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1 class="page-title">Admin</h1>
    <p class="subtitle">{{ total }} users</p>

    <div v-if="error" class="banner error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="load">Retry</button>
    </div>
    <div v-if="message" class="banner ok-banner">{{ message }}</div>

    <div v-if="loading" class="skeletons">
      <div v-for="n in 3" :key="n" class="card item-skeleton">
        <div class="line-skeleton w60"></div>
        <div class="line-skeleton w40"></div>
      </div>
    </div>

    <div v-else-if="users.length === 0" class="empty card">
      <p class="empty-title">No users found.</p>
    </div>

    <div v-else class="user-list">
      <div v-for="u in users" :key="u.id" class="card user-row">
        <div class="user-main">
          <p class="user-name">
            {{ u.username }}
            <span class="role-badge" :class="u.role">{{ u.role }}</span>
          </p>
          <p class="user-meta">{{ u.email }} · joined {{ formatDate(u.created_at) }}</p>
        </div>
        <div class="user-actions">
          <select v-model="roleSelect[u.id]" :disabled="busy[u.id]" @change="changeRole(u)">
            <option v-for="r in ROLES" :key="r" :value="r">{{ r }}</option>
          </select>
          <button
            class="btn danger-btn"
            :disabled="busy[u.id]"
            @click="deactivate(u)"
          >Deactivate</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 13px;
  margin: -12px 0 16px;
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

.ok-banner {
  background: color-mix(in srgb, #2e7d32 12%, transparent);
  border: 1px solid #2e7d32;
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
  margin: 0;
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  flex-wrap: wrap;
}

.user-main {
  min-width: 0;
}

.user-name {
  margin: 0 0 2px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.role-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.role-badge.admin {
  color: var(--accent);
  border-color: var(--accent);
}

.role-badge.moderator {
  color: #2e7d32;
  border-color: #2e7d32;
}

.user-meta {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.user-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.user-actions select {
  background: var(--input-bg);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 6px 10px;
  font: inherit;
  font-size: 13px;
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

.danger-btn {
  color: var(--danger);
}
</style>
