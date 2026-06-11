/** M01 routes (FDD §2.1.2 UI pages). Login pages render outside the shell. */
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginPage.vue'),
    meta: { public: true },
  },
  {
    path: '/login/verify',
    name: 'login-verify',
    component: () => import('@/views/auth/VerifyPage.vue'),
    meta: { public: true },
  },
  {
    path: '/account/session',
    name: 'account-session',
    component: () => import('@/views/auth/SessionPage.vue'),
    meta: { title: 'Session' },
  },
]

export default routes
