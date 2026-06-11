/** M03 routes (FDD §2.3.2 UI pages). */
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('@/views/iam/UsersPage.vue'),
    meta: { title: 'Users' },
  },
  {
    path: '/admin/users/:userId',
    name: 'admin-user-detail',
    component: () => import('@/views/iam/UserDetailPage.vue'),
    meta: { title: 'User' },
  },
  {
    path: '/admin/permissions',
    name: 'admin-permissions',
    component: () => import('@/views/iam/PermissionsPage.vue'),
    meta: { title: 'Permissions' },
  },
  {
    path: '/admin/roles',
    name: 'admin-roles',
    component: () => import('@/views/iam/RolesPage.vue'),
    meta: { title: 'Roles', scope: 'platform' },
  },
  {
    path: '/tenant/roles',
    name: 'tenant-roles',
    component: () => import('@/views/iam/RolesPage.vue'),
    meta: { title: 'Roles', scope: 'tenant' },
  },
  {
    path: '/admin/role-bindings',
    name: 'admin-role-bindings',
    component: () => import('@/views/iam/RoleBindingsPage.vue'),
    meta: { title: 'Role bindings', scope: 'platform' },
  },
  {
    path: '/tenant/role-bindings',
    name: 'tenant-role-bindings',
    component: () => import('@/views/iam/RoleBindingsPage.vue'),
    meta: { title: 'Role bindings', scope: 'tenant' },
  },
  {
    path: '/admin/audit',
    name: 'admin-audit',
    component: () => import('@/views/iam/AuditPage.vue'),
    meta: { title: 'Audit', scope: 'platform' },
  },
  {
    path: '/tenant/audit',
    name: 'tenant-audit',
    component: () => import('@/views/iam/AuditPage.vue'),
    meta: { title: 'Audit', scope: 'tenant' },
  },
  {
    path: '/tenant/access-reviews',
    name: 'tenant-access-reviews',
    component: () => import('@/views/iam/AccessReviewsPage.vue'),
    meta: { title: 'Access reviews' },
  },
]

export default routes
