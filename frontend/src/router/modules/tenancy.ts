/** M02 routes (FDD §2.2.2 UI pages). */
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/admin/tenants',
    name: 'admin-tenants',
    component: () => import('@/views/tenancy/TenantsAdminPage.vue'),
    meta: { title: 'Tenants' },
  },
  {
    path: '/admin/tenants/:tenantId',
    name: 'admin-tenant-detail',
    component: () => import('@/views/tenancy/TenantDetailPage.vue'),
    meta: { title: 'Tenant' },
  },
  {
    path: '/admin/resources',
    name: 'admin-resources',
    component: () => import('@/views/tenancy/ResourcesPage.vue'),
    meta: { title: 'Resources' },
  },
  {
    path: '/tenant',
    name: 'tenant-self',
    component: () => import('@/views/tenancy/TenantSelfPage.vue'),
    meta: { title: 'Tenant' },
  },
  {
    path: '/tenant/projects',
    name: 'tenant-projects',
    component: () => import('@/views/tenancy/ProjectsPage.vue'),
    meta: { title: 'Projects' },
  },
  {
    path: '/projects/:projectId',
    name: 'project-detail',
    component: () => import('@/views/tenancy/ProjectDetailPage.vue'),
    meta: { title: 'Project' },
  },
]

export default routes
