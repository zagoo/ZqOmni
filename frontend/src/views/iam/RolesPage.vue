<script setup lang="ts">
/** M03 UI page 4 — Role management & composer, /admin/roles (PA) and
 * /tenant/roles (TA). Built-ins render locked with their expanded unit list;
 * the composer's dual-list recombines catalog units (anti-escalation is
 * server-enforced). */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import ModalDialog from '@/components/ModalDialog.vue'
import AppIcon from '@/components/AppIcon.vue'
import { describeApiError, useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import {
  m03CreateTenantRole,
  m03DeleteRole,
  m03UpdateRole,
  type RoleOut,
} from '@/views/iam/api'
import { usePermissionCatalog, useRoleList } from '@/views/iam/hooks/useIam'

const route = useRoute()
const toast = useToast()
const auth = useAuthStore()
const surface = (route.meta.scope as 'platform' | 'tenant') ?? 'tenant'

const roles = useRoleList(surface)
const catalog = usePermissionCatalog()
onMounted(async () => {
  await Promise.all([roles.load(), catalog.load()])
})

const canCompose = computed(() => auth.can('iam.role:create') && !!auth.activeTenantId)

// --- Composer ---
const composerOpen = ref(false)
const composerError = ref('')
const editingRole = ref<RoleOut | null>(null)
const composer = reactive({ name: '', description: '', keys: new Set<string>(), filter: '' })
const saving = ref(false)

const grantableUnits = computed(() =>
  catalog.items.value.filter(
    (p) =>
      !p.service_only &&
      (!composer.filter ||
        p.key.includes(composer.filter) ||
        p.description.toLowerCase().includes(composer.filter.toLowerCase())),
  ),
)

function openComposer(role?: RoleOut) {
  composerError.value = ''
  editingRole.value = role ?? null
  composer.name = role?.name ?? ''
  composer.description = role?.description ?? ''
  composer.keys = new Set(role?.permission_keys ?? [])
  composer.filter = ''
  composerOpen.value = true
}

function toggleKey(key: string) {
  composer.keys.has(key) ? composer.keys.delete(key) : composer.keys.add(key)
}

async function saveRole() {
  if (composer.name.trim().length < 2) {
    composerError.value = 'Role name must be 2–64 characters.'
    return
  }
  if (composer.keys.size === 0) {
    composerError.value = 'Select at least one permission unit.'
    return
  }
  saving.value = true
  try {
    if (editingRole.value) {
      await m03UpdateRole({
        path: { role_id: editingRole.value.role_id },
        headers: { 'If-Match': `"${editingRole.value.version}"` },
        body: { description: composer.description || null, permission_keys: [...composer.keys] },
        throwOnError: true,
      })
      toast.success('Role updated. Active sessions pick up changes within 60 seconds.')
    } else {
      if (!auth.activeTenantId) return
      await m03CreateTenantRole({
        path: { tenant_id: auth.activeTenantId },
        body: {
          name: composer.name.trim(),
          description: composer.description || null,
          permission_keys: [...composer.keys],
        },
        throwOnError: true,
      })
      toast.success('Role created.')
    }
    composerOpen.value = false
    await roles.load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    composerError.value =
      errorCode === 'E_IAM_BUILTIN_IMMUTABLE'
        ? 'Built-in roles cannot be modified.'
        : errorCode === 'E_PERMISSION_DENIED'
          ? 'You cannot grant permissions outside your own effective set.'
          : message
  } finally {
    saving.value = false
  }
}

async function deleteRole(role: RoleOut) {
  try {
    await m03DeleteRole({ path: { role_id: role.role_id }, throwOnError: true })
    toast.success('Role deleted.')
    await roles.load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    toast.error(
      errorCode === 'E_IAM_ROLE_IN_USE'
        ? 'Role has active bindings; remove them first.'
        : errorCode === 'E_IAM_BUILTIN_IMMUTABLE'
          ? 'Built-in roles cannot be deleted.'
          : message,
    )
  }
}
</script>

<template>
  <div>
    <div class="page-header-row">
      <h1 class="text-display">Roles</h1>
      <button v-if="canCompose" class="btn btn-primary" type="button" @click="openComposer()">
        Compose role
      </button>
    </div>

    <div v-if="roles.loading.value" class="card-grid">
      <div v-for="i in 4" :key="i" class="skeleton" style="height: 140px" />
    </div>
    <div v-else class="card-grid">
      <div v-for="role in roles.items.value" :key="role.role_id" class="card role-card">
        <div class="role-head">
          <span class="text-h5 role-name">
            <AppIcon v-if="role.role_type === 'builtin'" name="lock" :size="16" />
            {{ role.name }}
          </span>
          <span class="badge" :class="role.role_type === 'builtin' ? 'badge-neutral' : 'badge-purple'">
            {{ role.role_type }}
          </span>
        </div>
        <p class="text-caption">{{ role.description || '—' }}</p>
        <p class="text-caption">
          {{ role.permission_keys.length }} unit(s) · {{ role.bindings_count ?? 0 }} binding(s)
        </p>
        <div class="role-actions">
          <button class="btn btn-secondary btn-sm" type="button" @click="openComposer(role)">
            {{ role.role_type === 'builtin' ? 'View units' : 'Recompose' }}
          </button>
          <button
            v-if="role.role_type === 'custom'"
            class="btn btn-ghost btn-sm"
            type="button"
            @click="deleteRole(role)"
          >
            Delete
          </button>
        </div>
      </div>
    </div>

    <ModalDialog
      :title="editingRole ? (editingRole.role_type === 'builtin' ? `${editingRole.name} (read-only)` : 'Recompose role') : 'Compose role'"
      :open="composerOpen"
      wide
      @close="composerOpen = false"
    >
      <p v-if="composerError" class="banner-error">{{ composerError }}</p>
      <div class="field">
        <label class="field-label">Name</label>
        <input
          v-model="composer.name"
          class="text-input"
          maxlength="64"
          placeholder="annotation-vendor-lead"
          :disabled="editingRole !== null"
        />
      </div>
      <div class="field">
        <label class="field-label">Description</label>
        <input
          v-model="composer.description"
          class="text-input"
          maxlength="500"
          :disabled="editingRole?.role_type === 'builtin'"
        />
      </div>
      <div class="field">
        <label class="field-label">Permission units ({{ composer.keys.size }} selected)</label>
        <input v-model="composer.filter" class="search-pill" placeholder="Filter permissions…" />
        <div class="unit-list">
          <label v-for="p in grantableUnits" :key="p.key" class="unit-row">
            <input
              type="checkbox"
              :checked="composer.keys.has(p.key)"
              :disabled="editingRole?.role_type === 'builtin'"
              @change="toggleKey(p.key)"
            />
            <code class="unit-key">{{ p.key }}</code>
            <span class="text-caption unit-desc">{{ p.description }}</span>
          </label>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="composerOpen = false">Close</button>
        <button
          v-if="editingRole?.role_type !== 'builtin'"
          class="btn btn-primary"
          type="button"
          :disabled="saving"
          @click="saveRole"
        >
          {{ saving ? 'Saving…' : editingRole ? 'Save role' : 'Create role' }}
        </button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.role-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  align-items: flex-start;
}
.role-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: var(--space-sm);
}
.role-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.role-actions {
  display: flex;
  gap: var(--space-xs);
  margin-top: var(--space-xs);
}
.unit-list {
  max-height: 280px;
  overflow-y: auto;
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-md);
  margin-top: var(--space-xs);
  padding: var(--space-xs);
}
.unit-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 4px 6px;
  border-radius: var(--rounded-xs);
}
.unit-row:nth-child(odd) {
  background: var(--color-surface-soft);
}
.unit-key {
  font-size: 13px;
  white-space: nowrap;
}
.unit-desc {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
