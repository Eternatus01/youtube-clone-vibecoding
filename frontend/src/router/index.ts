import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../pages/HomePage.vue'),
    },
    {
      path: '/watch/:id',
      name: 'watch',
      component: () => import('../pages/WatchPage.vue'),
    },
    {
      path: '/channel/:id',
      name: 'channel',
      component: () => import('../pages/ChannelPage.vue'),
    },
    {
      path: '/channel/edit',
      name: 'channel-edit',
      component: () => import('../pages/ChannelEditPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('../pages/SearchPage.vue'),
    },
    {
      path: '/playlist/:id',
      name: 'playlist',
      component: () => import('../pages/PlaylistPage.vue'),
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('../pages/UploadPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/my-videos',
      name: 'my-videos',
      component: () => import('../pages/MyVideosPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/moderation',
      name: 'moderation',
      component: () => import('../pages/ModerationPage.vue'),
      meta: { requiresRole: ['moderator', 'admin'] },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../pages/AdminPage.vue'),
      meta: { requiresRole: ['admin'] },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../pages/RegisterPage.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../pages/HistoryPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/subscriptions',
      name: 'subscriptions',
      component: () => import('../pages/SubscriptionsPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: { name: 'home' },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()

  // UX-only guard; the server enforces real authorization.
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { name: 'home' }
  }
  const roles = to.meta.requiresRole as string[] | undefined
  if (roles && (!auth.user || !roles.includes(auth.user.role))) {
    return { name: 'home' }
  }
})
