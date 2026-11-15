import { createRouter, createWebHistory } from 'vue-router'

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
      path: '/upload',
      name: 'upload',
      component: () => import('../pages/UploadPage.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
    },
  ],
})
