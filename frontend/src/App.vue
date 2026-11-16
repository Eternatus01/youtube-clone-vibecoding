<script setup lang="ts">
import { onBeforeUnmount, onMounted, computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

type Theme = 'light' | 'dark'

const THEME_KEY = 'yt-theme'
const SIDEBAR_KEY = 'yt-sidebar-collapsed'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

auth.init()

// ---- Theme (persisted, default dark) ----
const theme = ref<Theme>((localStorage.getItem(THEME_KEY) as Theme) || 'dark')

function applyTheme(t: Theme) {
  document.documentElement.dataset.theme = t
}

watch(
  theme,
  (t) => {
    applyTheme(t)
    localStorage.setItem(THEME_KEY, t)
  },
  { immediate: true },
)

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

// ---- Sidebar collapse (persisted) ----
const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_KEY) === '1')

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem(SIDEBAR_KEY, sidebarCollapsed.value ? '1' : '0')
}

// ---- Search ----
const searchQuery = ref('')

watch(
  () => route.query.q,
  (v) => {
    searchQuery.value = typeof v === 'string' ? v : ''
  },
  { immediate: true },
)

function submitSearch() {
  const q = searchQuery.value.trim()
  router.push({ name: 'search', query: q ? { q } : {} })
}

// ---- User menu ----
const menuOpen = ref(false)

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function onDocumentClick(e: MouseEvent) {
  if (menuOpen.value && !(e.target as HTMLElement).closest('.user-menu')) {
    menuOpen.value = false
  }
}

async function logout() {
  menuOpen.value = false
  await auth.logout()
  router.push({ name: 'home' })
}

function closeMenu() {
  menuOpen.value = false
}

// Role-based link visibility (UX only; the server enforces real authorization).
const canModerate = computed(() => auth.user?.role === 'moderator' || auth.user?.role === 'admin')
const isAdmin = computed(() => auth.user?.role === 'admin')

onMounted(() => document.addEventListener('click', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick))

const initials = () =>
  (auth.user?.username ?? '?')
    .split(/[\s_-]+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="topbar-left">
        <button class="icon-btn" aria-label="Toggle sidebar" @click="toggleSidebar">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 6h18v2H3V6zm0 5h18v2H3v-2zm0 5h18v2H3v-2z" />
          </svg>
        </button>
        <RouterLink to="/" class="logo">
          <span class="logo-icon">
            <svg width="26" height="18" viewBox="0 0 28 20" fill="none">
              <rect width="28" height="20" rx="5" fill="#ff0033" />
              <path d="M11 5.5v9l7.5-4.5L11 5.5z" fill="#fff" />
            </svg>
          </span>
          <span class="logo-text">YouTube</span>
        </RouterLink>
      </div>

      <form class="search" role="search" @submit.prevent="submitSearch">
        <input
          v-model="searchQuery"
          class="search-input"
          type="search"
          placeholder="Search"
          aria-label="Search videos"
        />
        <button class="search-btn" type="submit" aria-label="Search">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 1 0-.7.7l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"
            />
          </svg>
        </button>
      </form>

      <div class="topbar-right">
        <RouterLink to="/upload" class="btn upload-btn" title="Upload video">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 4l6 6h-4v7h-4v-7H6l6-6z" />
          </svg>
          <span>Upload</span>
        </RouterLink>

        <button
          class="icon-btn"
          :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
          @click="toggleTheme"
        >
          <svg v-if="theme === 'dark'" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0-3a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V5a1 1 0 0 1 1-1zm0 14a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1zM4 11h1a1 1 0 1 1 0 2H4a1 1 0 1 1 0-2zm15 0h1a1 1 0 1 1 0 2h-1a1 1 0 1 1 0-2zM5.6 4.2l.7.7.7.7a1 1 0 0 1-1.4 1.4l-.7-.7-.7-.7a1 1 0 0 1 1.4-1.4zm11.4 11.4.7.7.7.7a1 1 0 0 1-1.4 1.4l-.7-.7-.7-.7a1 1 0 0 1 1.4-1.4z"
            />
          </svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M12.3 3a9 9 0 1 0 8.7 11.3A7.5 7.5 0 0 1 12.3 3z"
            />
          </svg>
        </button>

        <RouterLink v-if="!auth.isAuthenticated" to="/login" class="btn login-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-3.3 0-8 1.7-8 5v1h16v-1c0-3.3-4.7-5-8-5z" />
          </svg>
          <span>Sign in</span>
        </RouterLink>

        <div v-else class="user-menu">
          <button class="avatar" :title="auth.user?.username" @click="toggleMenu">
            <img
              v-if="auth.user?.avatar_url"
              :src="auth.user.avatar_url"
              :alt="auth.user.username"
            />
            <span v-else>{{ initials() }}</span>
          </button>
          <div v-if="menuOpen" class="menu-dropdown">
            <div class="menu-header">
              <div class="menu-username">{{ auth.user?.username }}</div>
              <div class="menu-email">{{ auth.user?.email }}</div>
            </div>
            <!-- Dropdown only renders when authenticated; server enforces the rest. -->
            <RouterLink
              v-if="auth.user"
              :to="`/channel/${auth.user.id}`"
              class="menu-item"
              @click="closeMenu"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm0 12c4.4 0 8 2 8 4.5V21H4v-2.5C4 16 7.6 14 12 14z" />
              </svg>
              Мой канал
            </RouterLink>
            <RouterLink to="/my-videos" class="menu-item" @click="closeMenu">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M4 6h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1zm5 3v6l5-3-5-3z" />
              </svg>
              Your videos
            </RouterLink>
            <RouterLink v-if="canModerate" to="/moderation" class="menu-item" @click="closeMenu">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2l8 4v6c0 5-3.4 9.4-8 10-4.6-.6-8-5-8-10V6l8-4zm-1 12l6-6-1.4-1.4L11 11.2 8.4 8.6 7 10l4 4z" />
              </svg>
              Moderation
            </RouterLink>
            <RouterLink v-if="isAdmin" to="/admin" class="menu-item" @click="closeMenu">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 1l3 5 6 1-4 5 1 6-6-3-6 3 1-6-4-5 6-1 3-5z" />
              </svg>
              Admin
            </RouterLink>
            <button class="menu-item" @click="logout">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M10 3h4a2 2 0 0 1 2 2v3h-2V5h-4v14h4v-3h2v3a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zm9 6 4 3-4 3v-2h-6v-2h6V9z" />
              </svg>
              Sign out
            </button>
          </div>
        </div>
      </div>
    </header>

    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <nav>
        <RouterLink to="/" class="side-link" :class="{ active: route.name === 'home' }">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 3l9 8h-3v9h-4v-6H10v6H6v-9H3l9-8z" />
          </svg>
          <span class="side-label">Home</span>
        </RouterLink>
        <RouterLink
          to="/subscriptions"
          class="side-link"
          :class="{ active: route.name === 'subscriptions' }"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <path d="M4 6h16v2H4V6zm2-3h12v2H6V3zm-2 7h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1zm6 2.5v6l5-3-5-3z" />
          </svg>
          <span class="side-label">Подписки</span>
        </RouterLink>
        <RouterLink
          to="/history"
          class="side-link"
          :class="{ active: route.name === 'history' }"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <path d="M13 3a9 9 0 1 0 8.94 10h-2.02A7 7 0 1 1 13 5c1.93 0 3.68.79 4.95 2.05L15 10h7V3l-2.65 2.65A8.96 8.96 0 0 0 13 3zm-1 5v5l4.25 2.52.77-1.28-3.52-2.09V8H12z" />
          </svg>
          <span class="side-label">История</span>
        </RouterLink>
        <RouterLink
          v-if="auth.isAuthenticated"
          to="/my-videos"
          class="side-link"
          :class="{ active: route.name === 'my-videos' }"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <path d="M4 6h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1zm5 3v6l5-3-5-3z" />
          </svg>
          <span class="side-label">Your videos</span>
        </RouterLink>
        <RouterLink to="/upload" class="side-link" :class="{ active: route.name === 'upload' }">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 4l6 6h-4v7h-4v-7H6l6-6zM5 19h14v2H5v-2z" />
          </svg>
          <span class="side-label">Upload</span>
        </RouterLink>
      </nav>
    </aside>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app {
  display: grid;
  grid-template-rows: var(--topbar-h) 1fr;
  grid-template-columns: auto 1fr;
  height: 100vh;
}

/* ---- Topbar ---- */
.topbar {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 16px;
  background: var(--bg);
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid var(--border);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
}

.logo-icon {
  display: flex;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.search {
  display: flex;
  flex: 1;
  max-width: 560px;
  margin: 0 16px;
}

.search-input {
  flex: 1;
  padding: 0 14px;
  height: 38px;
  border: 1px solid var(--border);
  border-right: none;
  border-radius: 20px 0 0 20px;
  background: var(--input-bg);
  color: var(--text);
  font: inherit;
}

.search-input:focus {
  outline: none;
  border-color: var(--accent);
}

.search-btn {
  width: 60px;
  height: 38px;
  border: 1px solid var(--border);
  border-radius: 0 20px 20px 0;
  background: var(--bg-elevated);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-btn:hover {
  background: var(--bg-hover);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.upload-btn svg {
  display: none;
}

/* ---- User menu ---- */
.user-menu {
  position: relative;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.menu-dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 220px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  z-index: 200;
}

.menu-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.menu-username {
  font-weight: 600;
}

.menu-email {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: 2px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 16px;
  text-align: left;
}

.menu-item:hover {
  background: var(--bg-hover);
}

/* ---- Sidebar ---- */
.sidebar {
  grid-row: 2;
  width: var(--sidebar-w);
  padding: 12px 8px;
  overflow-y: auto;
  border-right: 1px solid var(--border);
  position: sticky;
  top: var(--topbar-h);
  height: calc(100vh - var(--topbar-h));
}

.sidebar nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  position: sticky;
  top: 0;
}

.side-link {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--text);
  white-space: nowrap;
}

.side-link:hover {
  background: var(--bg-hover);
}

.side-link.active {
  background: var(--bg-elevated);
  font-weight: 600;
}

/* Visually disabled placeholder links (pages not implemented yet). */
.side-link.dead-link {
  opacity: 0.5;
  cursor: default;
}

.side-link.dead-link:hover {
  background: none;
}

.side-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar.collapsed {
  width: var(--sidebar-mini-w);
  padding: 12px 4px;
}

.sidebar.collapsed .side-link {
  flex-direction: column;
  gap: 6px;
  padding: 12px 4px;
  font-size: 10px;
  text-align: center;
}

.sidebar.collapsed .side-label {
  max-width: 64px;
}

/* ---- Content ---- */
.content {
  grid-row: 2;
  overflow-y: auto;
  min-width: 0;
}

@media (max-width: 792px) {
  .upload-btn span {
    display: none;
  }
  .upload-btn svg {
    display: block;
  }
  .search {
    margin: 0 8px;
  }
}

@media (max-width: 640px) {
  .sidebar {
    display: none;
  }
  .content {
    grid-column: 1 / -1;
  }
  .upload-btn span {
    display: none;
  }
  .upload-btn svg {
    display: block;
  }
  .login-btn span {
    display: none;
  }
}
</style>
