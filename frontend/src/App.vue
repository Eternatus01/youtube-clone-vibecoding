<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Component } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  ChevronLeft,
  Film,
  History,
  Home,
  Menu,
  Moon,
  Play,
  PlaySquare,
  Search,
  Sun,
  UserCircle,
  Video,
} from 'lucide-vue-next'
import { useAuthStore } from './stores/auth'
import { useToast } from './composables/useToast'

type Theme = 'light' | 'dark'

const THEME_KEY = 'yt-theme'
const SIDEBAR_KEY = 'yt-sidebar-collapsed'
const MOBILE_BREAKPOINT = '(max-width: 792px)'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { toasts, push } = useToast()

auth.init()

// ---- Theme (persisted; falls back to prefers-color-scheme on first load) ----
const storedTheme = localStorage.getItem(THEME_KEY)
const prefersLight =
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-color-scheme: light)').matches
const theme = ref<Theme>(
  storedTheme === 'light' || storedTheme === 'dark' ? storedTheme : prefersLight ? 'light' : 'dark',
)

watch(
  theme,
  (t) => {
    document.documentElement.dataset.theme = t
  },
  { immediate: true },
)

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem(THEME_KEY, theme.value)
}

// ---- Sidebar: desktop collapse (persisted) + mobile overlay drawer ----
const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_KEY) === '1')
const mobileNavOpen = ref(false)
const isMobile = ref(
  typeof window.matchMedia === 'function' && window.matchMedia(MOBILE_BREAKPOINT).matches,
)

function onMediaChange(e: MediaQueryListEvent) {
  isMobile.value = e.matches
  if (!e.matches) mobileNavOpen.value = false
}

onMounted(() => {
  const mql = window.matchMedia(MOBILE_BREAKPOINT)
  mql.addEventListener('change', onMediaChange)
  onBeforeUnmount(() => mql.removeEventListener('change', onMediaChange))
  document.addEventListener('click', onDocumentClick)
})
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick))

function toggleSidebar() {
  if (isMobile.value) {
    mobileNavOpen.value = !mobileNavOpen.value
    return
  }
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem(SIDEBAR_KEY, sidebarCollapsed.value ? '1' : '0')
}

function onCollapseClick() {
  if (isMobile.value) mobileNavOpen.value = false
  else toggleSidebar()
}

function closeMobileNav() {
  mobileNavOpen.value = false
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

// ---- Sidebar navigation ----
interface NavItem {
  to: string
  name: string
  label: string
  icon: Component
}

const navItems: NavItem[] = [
  { to: '/', name: 'home', label: 'Главная', icon: Home },
  { to: '/subscriptions', name: 'subscriptions', label: 'Подписки', icon: PlaySquare },
  { to: '/history', name: 'history', label: 'История', icon: History },
  { to: '/my-videos', name: 'my-videos', label: 'Мои видео', icon: Film },
]

// ---- User menu ----
const menuOpen = ref(false)

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function closeMenu() {
  menuOpen.value = false
}

function onDocumentClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (menuOpen.value && !target.closest('.user-menu')) {
    menuOpen.value = false
  }
  // Mobile search overlay: any click outside it (and outside the icon) closes it.
  if (
    searchOpen.value &&
    !target.closest('.search-overlay') &&
    !target.closest('.search-icon-btn')
  ) {
    searchOpen.value = false
  }
}

// ---- Mobile search overlay (icon button below 792px) ----
const searchOpen = ref(false)
const overlayInput = ref<HTMLInputElement | null>(null)

function toggleSearchOverlay() {
  searchOpen.value = !searchOpen.value
  if (searchOpen.value) {
    nextTick(() => overlayInput.value?.focus())
  }
}

function submitOverlaySearch() {
  submitSearch()
  searchOpen.value = false
}

watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false
    searchOpen.value = false
    closeMobileNav()
  },
)

async function logout() {
  menuOpen.value = false
  await auth.logout()
  router.push({ name: 'home' })
  push('Вы вышли из аккаунта')
}

// First letter of the username for the avatar circle.
const firstLetter = computed(() => (auth.user?.username ?? '?').charAt(0).toUpperCase())
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="topbar-left">
        <button class="icon-btn" aria-label="Меню" @click="toggleSidebar">
          <Menu class="lucide-icon" :size="24" />
        </button>
        <RouterLink to="/" class="logo" aria-label="На главную">
          <span class="logo-mark">
            <Play class="lucide-icon" :size="12" fill="currentColor" />
          </span>
          <span class="logo-text">YouTube</span>
        </RouterLink>
      </div>

      <form class="search" role="search" @submit.prevent="submitSearch">
        <Search class="search-glass" :size="20" aria-hidden="true" />
        <input
          v-model="searchQuery"
          class="search-input"
          type="search"
          placeholder="Поиск"
          aria-label="Поиск видео"
        />
        <button class="search-btn" type="submit" aria-label="Найти">
          <Search class="lucide-icon" :size="24" />
        </button>
      </form>

      <!-- Mobile: search collapses to an icon that opens the overlay below the header. -->
      <button
        class="icon-btn search-icon-btn"
        type="button"
        aria-label="Поиск"
        @click="toggleSearchOverlay"
      >
        <Search class="lucide-icon" :size="24" />
      </button>

      <div class="topbar-right">
        <RouterLink to="/upload" class="upload-btn" title="Загрузить видео">
          <Video class="lucide-icon" :size="24" />
          <span>Загрузить</span>
        </RouterLink>

        <button
          class="icon-btn"
          :aria-label="theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'"
          @click="toggleTheme"
        >
          <!-- In dark mode show Sun (switch to light), in light mode Moon. -->
          <Sun v-if="theme === 'dark'" class="lucide-icon" :size="24" />
          <Moon v-else class="lucide-icon" :size="24" />
        </button>

        <RouterLink v-if="!auth.isAuthenticated" to="/login" class="login-btn">
          <UserCircle class="lucide-icon" :size="24" />
          <span>Войти</span>
        </RouterLink>

        <div v-else class="user-menu">
          <button class="avatar" :title="auth.user?.username" @click="toggleMenu">
            {{ firstLetter }}
          </button>
          <div v-if="menuOpen" class="menu-dropdown">
            <RouterLink
              v-if="auth.user"
              :to="`/channel/${auth.user.id}`"
              class="menu-item"
              @click="closeMenu"
            >
              Мой канал
            </RouterLink>
            <div class="menu-divider"></div>
            <button class="menu-item" @click="logout">Выйти</button>
          </div>
        </div>
      </div>
    </header>

    <!-- Mobile search overlay: full-width bar below the header. -->
    <div v-if="searchOpen" class="search-overlay">
      <form class="search-overlay-form" role="search" @submit.prevent="submitOverlaySearch">
        <input
          ref="overlayInput"
          v-model="searchQuery"
          class="search-overlay-input"
          type="search"
          placeholder="Поиск"
          aria-label="Поиск видео"
        />
        <button class="search-overlay-btn" type="submit" aria-label="Найти">
          <Search class="lucide-icon" :size="24" />
        </button>
      </form>
    </div>

    <div v-if="mobileNavOpen" class="scrim" @click="closeMobileNav"></div>

    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed, open: mobileNavOpen }">
      <nav>
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="item.to"
          class="side-link"
          :class="{ active: route.name === item.name }"
          @click="closeMobileNav"
        >
          <component :is="item.icon" class="lucide-icon" :size="20" />
          <span class="side-label">{{ item.label }}</span>
        </RouterLink>
      </nav>
      <button
        class="icon-btn collapse-btn"
        :aria-label="sidebarCollapsed ? 'Развернуть меню' : 'Свернуть меню'"
        @click="onCollapseClick"
      >
        <ChevronLeft class="lucide-icon" :size="20" />
      </button>
    </aside>

    <main class="content">
      <RouterView />
    </main>

    <div v-if="toasts.length" class="toast-container">
      <div v-for="t in toasts" :key="t.id" class="toast">{{ t.text }}</div>
    </div>
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
  border-bottom: 1px solid var(--divider);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text);
}

.icon-btn:hover {
  background: var(--surface-hover);
}

.logo {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
}

/* Brand red only on the logo mark. */
.logo-mark {
  width: 24px;
  height: 18px;
  border-radius: 4px;
  background: var(--brand-red);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

/* ---- Search: flex 1, max 640, 40px, rounded left input + rounded right button ---- */
.search {
  position: relative;
  display: flex;
  flex: 1;
  max-width: 640px;
  height: 40px;
  margin: 0 16px;
}

.search-glass {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-2);
  pointer-events: none;
}

.search-input {
  flex: 1;
  min-width: 0;
  height: 40px;
  padding: 0 16px 0 44px;
  border: 1px solid var(--divider);
  border-right: none;
  border-radius: 20px 0 0 20px;
  background: var(--surface);
  color: var(--text);
  font-size: 16px;
  font-family: inherit;
}

.search-input::placeholder {
  color: var(--text-2);
}

.search-input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -1px;
}

.search-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  padding: 0 20px;
  border: 1px solid var(--divider);
  border-left: none;
  border-radius: 0 20px 20px 0;
  background: var(--surface);
  color: var(--text);
}

.search-btn:hover {
  background: var(--surface-hover);
}

/* Mobile search: icon button hidden on desktop; overlay rendered on demand. */
.search-icon-btn {
  display: none;
}

.search-overlay {
  position: fixed;
  top: var(--topbar-h);
  left: 0;
  right: 0;
  z-index: 400;
  background: var(--bg);
  border-bottom: 1px solid var(--divider);
  padding: 8px 16px;
}

.search-overlay-form {
  display: flex;
  gap: 8px;
}

.search-overlay-input {
  flex: 1;
  min-width: 0;
  height: 40px;
  padding: 0 16px;
  border: 1px solid var(--divider);
  border-radius: 20px;
  background: var(--surface);
  color: var(--text);
  font-size: 16px;
  font-family: inherit;
}

.search-overlay-input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -1px;
}

.search-overlay-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--surface);
  color: var(--text);
  flex-shrink: 0;
}

.search-overlay-btn:hover {
  background: var(--surface-hover);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.upload-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 12px;
  border-radius: 18px;
  color: var(--text);
  font-size: 14px;
  font-weight: 500;
}

.upload-btn:hover {
  background: var(--surface-hover);
}

.login-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid var(--divider);
  border-radius: 18px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  font-weight: 500;
}

.login-btn:hover {
  background: var(--surface-hover);
}

/* ---- User menu ---- */
.user-menu {
  position: relative;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--surface);
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.menu-dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 160px;
  padding: 4px 0;
  background: var(--surface);
  border-radius: var(--radius);
  /* Subtle shadow only; no big soft shadows. */
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  z-index: 200;
}

.menu-item {
  display: block;
  width: 100%;
  padding: 8px 16px;
  text-align: left;
  font-size: 14px;
  color: var(--text);
}

.menu-item:hover {
  background: var(--surface-hover);
}

.menu-divider {
  height: 1px;
  margin: 4px 0;
  background: var(--divider);
}

/* ---- Sidebar: 240px expanded, 72px mini ---- */
.sidebar {
  grid-row: 2;
  display: flex;
  flex-direction: column;
  width: var(--sidebar-w);
  padding: 12px 8px;
  overflow-y: auto;
  border-right: 1px solid var(--divider);
  position: sticky;
  top: var(--topbar-h);
  height: calc(100vh - var(--topbar-h));
}

.sidebar nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.side-link {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 40px;
  padding: 0 12px;
  border-radius: 10px;
  color: var(--text);
  font-size: 14px;
  white-space: nowrap;
}

.side-link:hover {
  background: var(--surface-hover);
}

/* Active state is subtle: overlay-hover, no bold, not saturated. */
.side-link.active {
  background: var(--overlay-hover);
}

.side-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.collapse-btn {
  margin-top: auto;
  border-radius: 10px;
  align-self: flex-start;
}

.sidebar.collapsed {
  width: var(--sidebar-mini-w);
  padding: 12px 4px;
}

.sidebar.collapsed .side-link {
  justify-content: center;
  padding: 0;
}

.sidebar.collapsed .side-label {
  display: none;
}

.sidebar.collapsed .collapse-btn {
  align-self: center;
}

/* Mobile drawer: overlay below 792px. */
.scrim {
  display: none;
}

/* 1015–1311px: sidebar auto-collapses to mini (72px), no manual toggle. */
@media (max-width: 1312px) {
  .sidebar:not(.open) {
    width: var(--sidebar-mini-w);
    padding: 12px 4px;
  }

  .sidebar:not(.open) .side-link {
    justify-content: center;
    padding: 0;
  }

  .sidebar:not(.open) .side-label {
    display: none;
  }

  .sidebar:not(.open) .collapse-btn {
    display: none;
  }
}

@media (max-width: 792px) {
  .app {
    grid-template-columns: 1fr;
  }

  .scrim {
    display: block;
    position: fixed;
    top: var(--topbar-h);
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 250;
  }

  .sidebar {
    position: fixed;
    top: var(--topbar-h);
    left: 0;
    bottom: 0;
    width: var(--sidebar-w);
    z-index: 300;
    transform: translateX(-100%);
    transition: transform 0.15s ease;
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .sidebar.collapsed {
    width: var(--sidebar-w);
    padding: 12px 8px;
  }

  .sidebar.collapsed .side-link {
    justify-content: flex-start;
    padding: 0 12px;
  }

  .sidebar.collapsed .side-label {
    display: inline;
  }

  .sidebar.collapsed .collapse-btn {
    align-self: flex-start;
  }

  /* Sidebar is overlay-only here: drawer hidden until the hamburger opens it. */
  .sidebar:not(.open) {
    transform: translateX(-100%);
  }

  /* Search collapses to an icon that opens the overlay. */
  .search {
    display: none;
  }

  .search-icon-btn {
    display: flex;
  }

  .upload-btn span {
    display: none;
  }
}

@media (max-width: 640px) {
  .content {
    grid-column: 1 / -1;
  }

  .login-btn span {
    display: none;
  }

  .logo-text {
    display: none;
  }
}
</style>
