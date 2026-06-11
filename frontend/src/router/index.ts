/**
 * Routing hub (ARCHITECTURE §4.2) — auto-aggregates route modules from
 * ./modules via import.meta.glob. Never add routes here; create a module
 * file under router/modules instead.
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const moduleFiles = import.meta.glob<{ default: RouteRecordRaw[] }>('./modules/*.ts', {
  eager: true,
})

const routes: RouteRecordRaw[] = Object.values(moduleFiles).flatMap((m) => m.default)

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...routes,
    { path: '/', redirect: '/account/session' },
    { path: '/:pathMatch(.*)*', redirect: '/account/session' },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  const auth = useAuthStore()
  if (auth.isAuthenticated) return true
  if (await auth.bootstrap()) return true
  return { path: '/login', query: { redirect: to.fullPath } }
})
