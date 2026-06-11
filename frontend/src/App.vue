<script setup lang="ts">
/** Root viewport — owns the single <AppShell>. Routing changes the center
 * pane only (Rule 8.2); login pages render outside the shell. */
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/AppShell.vue'
import AppIcon from '@/components/AppIcon.vue'
import NavItem from '@/components/NavItem.vue'
import ToastHost from '@/components/ToastHost.vue'
import ToolbarIconButton from '@/components/ToolbarIconButton.vue'
import logoIcon from '@/assets/logo_icon.svg'
import { useToast } from '@/composables/useToast'
import { STUB_MODULES } from '@/router/modules/stubs'
import { useAuthStore } from '@/store/auth'
import { useShellStore } from '@/store/shell'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const shell = useShellStore()
const toast = useToast()

const inShell = computed(() => !route.meta.public)
const pageTitle = computed(() => (route.meta.title as string) ?? '')

const isPlatformAdmin = computed(() => auth.can('tenancy.tenant:create'))

interface NavEntry {
  icon: string
  label: string
  to: string
  visible: boolean
}

const platformNav = computed<NavEntry[]>(() => [
  { icon: 'building', label: 'My tenant', to: '/tenant', visible: auth.can('tenancy.tenant:read') && !!auth.activeTenantId },
  { icon: 'folder', label: 'Projects', to: '/tenant/projects', visible: auth.can('tenancy.project:read') && !!auth.activeTenantId },
  { icon: 'building', label: 'Tenants', to: '/admin/tenants', visible: auth.can('tenancy.tenant:create') },
  { icon: 'server', label: 'Resources', to: '/admin/resources', visible: auth.can('infra.resource:read') },
  { icon: 'users', label: 'Users', to: '/admin/users', visible: auth.can('iam.user:read') },
  { icon: 'key', label: 'Permissions', to: '/admin/permissions', visible: auth.can('iam.permission:read') },
  {
    icon: 'shield',
    label: 'Roles',
    to: isPlatformAdmin.value ? '/admin/roles' : '/tenant/roles',
    visible: auth.can('iam.role:read'),
  },
  {
    icon: 'link',
    label: 'Role bindings',
    to: isPlatformAdmin.value ? '/admin/role-bindings' : '/tenant/role-bindings',
    visible: auth.can('iam.role_binding:read'),
  },
  {
    icon: 'list',
    label: 'Audit',
    to: isPlatformAdmin.value ? '/admin/audit' : '/tenant/audit',
    visible: auth.can('audit.event:read'),
  },
  { icon: 'clipboard', label: 'Access reviews', to: '/tenant/access-reviews', visible: auth.can('iam.access_review:read') && !!auth.activeTenantId },
])

const stubGroups = computed(() => {
  const groups = new Map<string, typeof STUB_MODULES>()
  for (const m of STUB_MODULES) {
    const list = groups.get(m.group) ?? []
    list.push(m)
    groups.set(m.group, list)
  }
  return [...groups.entries()]
})

const expanded = ref<Record<string, boolean>>({ Platform: true })
function toggleGroup(name: string) {
  expanded.value[name] = !expanded.value[name]
}

const tenantMenuOpen = ref(false)
const activeTenantName = computed(() => {
  const t = auth.tenants.find((x) => x.tenant_id === auth.activeTenantId)
  return t?.name ?? 'No tenant'
})

async function pickTenant(tenantId: string) {
  tenantMenuOpen.value = false
  if (tenantId === auth.activeTenantId) return
  try {
    await auth.switchTenant(tenantId)
    toast.success('Active tenant switched.')
  } catch (e) {
    toast.apiError(e)
    await auth.loadCurrentSession()
  }
}

async function signOut() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <ToastHost />
  <template v-if="!inShell">
    <router-view />
  </template>
  <AppShell v-else>
    <!-- Product header: name + workspace (tenant) switcher (Rule 8.4) -->
    <template #nav-header>
      <div class="workspace-block">
        <button class="workspace-chip" type="button" @click="tenantMenuOpen = !tenantMenuOpen">
          <img class="workspace-logo" :src="logoIcon" alt="ZqOmni logo" />
          <span class="workspace-meta">
            <span class="workspace-name">ZqOmni</span>
            <span class="workspace-tenant">{{ activeTenantName }}</span>
          </span>
          <AppIcon name="chevron-down" :size="16" />
        </button>
        <div v-if="tenantMenuOpen" class="workspace-menu">
          <p class="text-micro-upper menu-caption">Tenants</p>
          <button
            v-for="t in auth.tenants"
            :key="t.tenant_id"
            class="workspace-menu-item"
            type="button"
            :disabled="t.status !== 'active'"
            @click="pickTenant(t.tenant_id)"
          >
            <span class="menu-item-name">{{ t.name }}</span>
            <span v-if="t.status === 'suspended'" class="badge badge-suspended">suspended</span>
            <AppIcon v-else-if="t.tenant_id === auth.activeTenantId" name="check-circle" :size="16" />
          </button>
          <p v-if="auth.tenants.length === 0" class="menu-empty">
            No tenant assigned yet. Contact your platform administrator.
          </p>
        </div>
      </div>
    </template>

    <!-- Primary nav: parents expand inline (Rule 8.5) -->
    <template #nav-primary>
      <NavItem
        icon="layers"
        label="Platform"
        expandable
        :expanded="expanded.Platform ?? false"
        @toggle="toggleGroup('Platform')"
      />
      <template v-if="expanded.Platform">
        <template v-for="entry in platformNav" :key="entry.to">
          <NavItem v-if="entry.visible" :icon="entry.icon" :label="entry.label" :to="entry.to" indent />
        </template>
      </template>
      <template v-for="[group, mods] in stubGroups" :key="group">
        <NavItem
          icon="box"
          :label="group"
          expandable
          :expanded="expanded[group] ?? false"
          @toggle="toggleGroup(group)"
        />
        <template v-if="expanded[group]">
          <NavItem v-for="m in mods" :key="m.id" :icon="m.icon" :label="m.name" :to="m.path" indent />
        </template>
      </template>
    </template>

    <!-- Utility links + user identity chip (Rule 8.4) -->
    <template #nav-footer>
      <NavItem
        icon="search"
        label="Search"
        @select="toast.info('Search ships with M18 Analytics & Mining (not implemented).')"
      />
      <NavItem
        icon="bell"
        label="What's new"
        @select="toast.info('Notifications ship with M20 (not implemented).')"
      />
      <NavItem icon="settings" label="Settings" to="/account/session" />
      <button v-if="auth.user" class="user-chip" type="button" @click="router.push('/account/session')">
        <img class="user-avatar" :src="logoIcon" alt="ZqOmni logo" />
        <span class="user-meta">
          <span class="user-name">{{ auth.user.display_name }}</span>
          <span class="user-email">{{ auth.user.email }}</span>
        </span>
        <span class="user-signout" title="Sign out" @click.stop="signOut">
          <AppIcon name="logout" :size="16" />
        </span>
      </button>
    </template>

    <!-- Center toolbar: collapse + title left; contextual actions right (Rule 8.6) -->
    <template #content-toolbar>
      <div class="toolbar-left">
        <ToolbarIconButton icon="panel-left" label="Toggle sidebar" @click="shell.toggleNav()" />
        <span class="toolbar-title">{{ pageTitle }}</span>
      </div>
      <div class="toolbar-right">
        <span id="shell-toolbar-actions" class="toolbar-actions" />
        <ToolbarIconButton icon="sliders" label="Toggle panel" @click="shell.togglePanel()" />
      </div>
    </template>

    <template #content>
      <router-view />
    </template>

    <!-- Right configuration panel targets (pages teleport into these) -->
    <template #panel-header>
      <div class="panel-header-row">
        <span id="shell-panel-title" class="panel-title">Details</span>
        <ToolbarIconButton icon="x" label="Close panel" @click="shell.closePanel()" />
      </div>
    </template>
    <template #panel-body>
      <div id="shell-panel-body" />
    </template>
  </AppShell>
</template>

<style scoped>
.workspace-block {
  position: relative;
}
.workspace-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: none;
  background: transparent;
  padding: 8px 10px;
  border-radius: var(--rounded-sm);
  cursor: pointer;
  font-family: var(--font-sans);
  color: var(--color-steel);
}
.workspace-chip:active {
  background: var(--color-hairline-soft);
}
.workspace-logo {
  width: 24px;
  height: 24px;
  flex: none;
  display: block;
}
.workspace-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}
.workspace-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-ink);
}
.workspace-tenant {
  font-size: 12px;
  color: var(--color-steel);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workspace-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 8px;
  right: 8px;
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-md);
  box-shadow: var(--shadow-modal);
  padding: var(--space-xs);
  z-index: 30;
}
.menu-caption {
  padding: 4px 8px;
}
.workspace-menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  border: none;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 14px;
  padding: 7px 8px;
  border-radius: var(--rounded-sm);
  cursor: pointer;
  color: var(--color-ink);
}
.workspace-menu-item:not(:disabled):active {
  background: var(--color-surface);
}
.workspace-menu-item:disabled {
  color: var(--color-muted);
  cursor: not-allowed;
}
.menu-item-name {
  flex: 1;
  text-align: left;
}
.menu-empty {
  font-size: 13px;
  color: var(--color-steel);
  padding: var(--space-xs);
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: none;
  background: transparent;
  border-top: 1px solid var(--color-hairline-soft);
  margin-top: var(--space-xs);
  padding: 10px;
  cursor: pointer;
  font-family: var(--font-sans);
}
.user-avatar {
  width: 26px;
  height: 26px;
  flex: none;
  display: block;
}
.user-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink);
}
.user-email {
  font-size: 12px;
  color: var(--color-steel);
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-signout {
  color: var(--color-steel);
  display: inline-flex;
  padding: 4px;
  border-radius: var(--rounded-sm);
}
.user-signout:active {
  background: var(--color-surface);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  flex: 1;
  min-width: 0;
}
.toolbar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-ink);
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}
.toolbar-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.panel-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.panel-title {
  font-size: 14px;
  font-weight: 600;
}
</style>
