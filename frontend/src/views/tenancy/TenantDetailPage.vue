<script setup lang="ts">
/** M02 UI pages 2+4 — Tenant detail & lifecycle with Profile · Resource
 * bindings · Projects tabs, /admin/tenants/{tenant_id} (PA). */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ModalDialog from '@/components/ModalDialog.vue'
import SegmentedControl from '@/components/SegmentedControl.vue'
import { describeApiError, useToast } from '@/composables/useToast'
import {
  m02CreateResourceBinding,
  m02ReactivateTenant,
  m02ReleaseResourceBinding,
  m02SuspendTenant,
  m02UpdateTenant,
  type ResourceOut,
} from '@/views/tenancy/api'
import {
  useBindingList,
  useProjectList,
  useResourceList,
  useTenantDetail,
} from '@/views/tenancy/hooks/useTenancy'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const tenantId = route.params.tenantId as string

const detail = useTenantDetail(tenantId)
const bindings = useBindingList(tenantId)
const projects = useProjectList(() => tenantId)
const resources = useResourceList()

const tab = ref('profile')
const tabs = [
  { value: 'profile', label: 'Profile' },
  { value: 'bindings', label: 'Resource bindings' },
  { value: 'projects', label: 'Projects' },
]

onMounted(async () => {
  await Promise.all([detail.load(), bindings.load(), projects.load()])
})

const tenant = computed(() => detail.tenant.value)

// --- Profile editing (If-Match optimistic locking) ---
const editForm = reactive({ display_name: '', description: '' })
const editing = ref(false)
function startEdit() {
  if (!tenant.value) return
  editForm.display_name = tenant.value.display_name
  editForm.description = tenant.value.description ?? ''
  editing.value = true
}
async function saveEdit() {
  if (!tenant.value || !detail.etag.value) return
  try {
    await m02UpdateTenant({
      path: { tenant_id: tenantId },
      headers: { 'If-Match': detail.etag.value },
      body: { display_name: editForm.display_name, description: editForm.description },
      throwOnError: true,
    })
    editing.value = false
    toast.success('Tenant updated.')
    await detail.load()
  } catch (e) {
    const { errorCode } = describeApiError(e)
    if (errorCode === 'E_PRECONDITION_FAILED') {
      toast.error('This tenant changed since you loaded it. Reload.')
      await detail.load()
    } else {
      toast.apiError(e)
    }
  }
}

// --- Lifecycle ---
const suspendOpen = ref(false)
const suspendReason = ref('')
const archiveOpen = ref(false)
const archiveConfirmName = ref('')

async function suspend() {
  try {
    await m02SuspendTenant({
      path: { tenant_id: tenantId },
      body: { reason: suspendReason.value },
      throwOnError: true,
    })
    toast.success('Tenant suspended.')
    suspendOpen.value = false
    await detail.load()
  } catch (e) {
    toast.apiError(e)
  }
}
async function reactivate() {
  try {
    await m02ReactivateTenant({ path: { tenant_id: tenantId }, throwOnError: true })
    toast.success('Tenant reactivated.')
    await detail.load()
  } catch (e) {
    toast.apiError(e)
  }
}
async function archive() {
  if (!detail.etag.value || archiveConfirmName.value !== tenant.value?.name) return
  try {
    await m02UpdateTenant({
      path: { tenant_id: tenantId },
      headers: { 'If-Match': detail.etag.value },
      body: { status: 'archived' },
      throwOnError: true,
    })
    toast.success('Tenant archived.')
    archiveOpen.value = false
    await detail.load()
  } catch (e) {
    toast.apiError(e)
  }
}

// --- Bind wizard (M02 UI page 4) ---
const bindOpen = ref(false)
const bindForm = reactive({ resource_id: '', binding_mode: 'exclusive', purpose: '' })
const bindError = ref('')

async function openBindWizard() {
  bindError.value = ''
  bindForm.resource_id = ''
  await resources.load()
  bindOpen.value = true
}

const bindableResources = computed(() =>
  resources.items.value.filter((r) => r.status === 'active'),
)
const selectedResource = computed<ResourceOut | undefined>(() =>
  resources.items.value.find((r) => r.resource_id === bindForm.resource_id),
)
const allowedModes = computed(() => {
  const r = selectedResource.value
  if (!r) return []
  if (r.resource_class === 'compute' && r.form === 'logical') return ['exclusive']
  if (r.resource_class === 'storage' && r.form === 'logical') {
    return tenant.value?.settings?.storage_isolation === 'dedicated_bucket'
      ? ['shared', 'exclusive']
      : ['shared']
  }
  return ['exclusive', 'shared']
})

async function bind() {
  if (!bindForm.resource_id) {
    bindError.value = 'Select a resource.'
    return
  }
  const mode = allowedModes.value.includes(bindForm.binding_mode)
    ? bindForm.binding_mode
    : allowedModes.value[0]
  try {
    await m02CreateResourceBinding({
      path: { tenant_id: tenantId },
      body: {
        resource_id: bindForm.resource_id,
        binding_mode: mode as 'exclusive' | 'shared',
        purpose: bindForm.purpose || null,
      },
      throwOnError: true,
    })
    toast.success('Resource bound. Scheduling targets update within seconds.')
    bindOpen.value = false
    await bindings.load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    bindError.value =
      errorCode === 'E_TNT_BINDING_CONFLICT'
        ? 'This resource is exclusively bound to another tenant.'
        : message
  }
}

async function release(bindingId: string) {
  try {
    await m02ReleaseResourceBinding({
      path: { tenant_id: tenantId, binding_id: bindingId },
      throwOnError: true,
    })
    toast.success('Binding released.')
    await bindings.load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    toast.error(
      errorCode === 'E_TNT_RESOURCE_IN_USE'
        ? 'Active workloads or stored data still reference this binding. Drain before release.'
        : message,
    )
  }
}
</script>

<template>
  <div v-if="tenant">
    <div class="page-header-row">
      <div>
        <h1 class="text-display">{{ tenant.display_name }}</h1>
        <p class="text-caption">{{ tenant.name }} · {{ tenant.namespace_ref }}</p>
      </div>
      <SegmentedControl v-model="tab" :options="tabs" />
    </div>

    <!-- Profile tab -->
    <div v-if="tab === 'profile'">
      <div class="card profile-card">
        <div class="profile-head">
          <span class="badge" :class="`badge-${tenant.status}`">{{ tenant.status }}</span>
          <span v-if="tenant.suspend_reason" class="text-caption">
            Reason: {{ tenant.suspend_reason }}
          </span>
        </div>
        <template v-if="!editing">
          <p class="text-sm field-block"><strong>Display name</strong> {{ tenant.display_name }}</p>
          <p class="text-sm field-block"><strong>Description</strong> {{ tenant.description || '—' }}</p>
          <p class="text-sm field-block">
            <strong>Storage isolation</strong> {{ tenant.settings?.storage_isolation }}
          </p>
          <button class="btn btn-secondary btn-sm" type="button" @click="startEdit">Edit profile</button>
        </template>
        <template v-else>
          <div class="field">
            <label class="field-label">Display name</label>
            <input v-model="editForm.display_name" class="text-input" maxlength="80" />
          </div>
          <div class="field">
            <label class="field-label">Description</label>
            <textarea v-model="editForm.description" class="textarea-input" maxlength="2000" />
          </div>
          <div class="edit-actions">
            <button class="btn btn-secondary btn-sm" type="button" @click="editing = false">Cancel</button>
            <button class="btn btn-primary btn-sm" type="button" @click="saveEdit">Save</button>
          </div>
        </template>
      </div>

      <div class="card lifecycle-card">
        <h3 class="text-h5">Lifecycle</h3>
        <p class="text-caption">
          Created {{ new Date(tenant.created_at).toLocaleString() }}
          <template v-if="tenant.suspended_at"> · Suspended {{ new Date(tenant.suspended_at).toLocaleString() }}</template>
          <template v-if="tenant.archived_at"> · Archived {{ new Date(tenant.archived_at).toLocaleString() }}</template>
        </p>
        <div class="lifecycle-actions">
          <button v-if="tenant.status === 'active'" class="btn btn-secondary" type="button" @click="suspendOpen = true">
            Suspend
          </button>
          <button v-if="tenant.status === 'suspended'" class="btn btn-secondary" type="button" @click="reactivate">
            Reactivate
          </button>
          <button
            v-if="tenant.status === 'suspended'"
            class="btn btn-danger"
            type="button"
            @click="archiveOpen = true"
          >
            Archive
          </button>
        </div>
      </div>
    </div>

    <!-- Resource bindings tab -->
    <div v-else-if="tab === 'bindings'">
      <div class="toolbar-row">
        <button class="btn btn-primary" type="button" :disabled="tenant.status !== 'active'" @click="openBindWizard">
          Bind resource
        </button>
      </div>
      <div v-if="bindings.items.value.length === 0" class="empty-state card">No bindings yet.</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Resource</th><th>Kind</th><th>Mode</th><th>Status</th><th>Bound</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in bindings.items.value" :key="b.binding_id">
            <td class="text-sm-medium">{{ b.resource_name }}</td>
            <td>{{ b.resource_class }}/{{ b.form }}</td>
            <td>{{ b.binding_mode }}</td>
            <td><span class="badge" :class="b.status === 'active' ? 'badge-active' : 'badge-neutral'">{{ b.status }}</span></td>
            <td class="text-caption">{{ new Date(b.bound_at).toLocaleString() }}</td>
            <td>
              <button v-if="b.status === 'active'" class="btn btn-ghost btn-sm" type="button" @click="release(b.binding_id)">
                Release
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Projects tab -->
    <div v-else>
      <div v-if="projects.items.value.length === 0" class="empty-state card">No projects.</div>
      <table v-else class="data-table">
        <thead>
          <tr><th>Project</th><th>Status</th><th>Members</th><th>Created</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="p in projects.items.value"
            :key="p.project_id"
            class="row-click"
            @click="router.push(`/projects/${p.project_id}`)"
          >
            <td class="text-sm-medium">{{ p.display_name }}</td>
            <td><span class="badge" :class="`badge-${p.status}`">{{ p.status }}</span></td>
            <td>{{ p.members_count ?? '—' }}</td>
            <td class="text-caption">{{ new Date(p.created_at).toLocaleDateString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Suspend dialog -->
    <ModalDialog title="Suspend tenant" :open="suspendOpen" @close="suspendOpen = false">
      <p class="banner-warning">
        All API access for this tenant will be blocked and running work paused via operations
        policy.
      </p>
      <div class="field">
        <label class="field-label">Reason (10–500 chars)</label>
        <textarea v-model="suspendReason" class="textarea-input" maxlength="500" />
      </div>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="suspendOpen = false">Cancel</button>
        <button class="btn btn-primary" type="button" :disabled="suspendReason.trim().length < 10" @click="suspend">
          Suspend
        </button>
      </template>
    </ModalDialog>

    <!-- Archive dialog (type-name-to-confirm) -->
    <ModalDialog title="Archive tenant" :open="archiveOpen" @close="archiveOpen = false">
      <p class="banner-error">
        Archiving is irreversible. All projects must be archived and all bindings released first.
      </p>
      <div class="field">
        <label class="field-label">Type the tenant name to confirm</label>
        <input v-model="archiveConfirmName" class="text-input" :placeholder="tenant.name" />
      </div>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="archiveOpen = false">Cancel</button>
        <button class="btn btn-danger" type="button" :disabled="archiveConfirmName !== tenant.name" @click="archive">
          Archive permanently
        </button>
      </template>
    </ModalDialog>

    <!-- Bind wizard -->
    <ModalDialog title="Bind resource" :open="bindOpen" wide @close="bindOpen = false">
      <p v-if="bindError" class="banner-error">{{ bindError }}</p>
      <div class="field">
        <label class="field-label">Resource</label>
        <select v-model="bindForm.resource_id" class="select-input">
          <option value="" disabled>Select resource…</option>
          <option v-for="r in bindableResources" :key="r.resource_id" :value="r.resource_id">
            {{ r.name }} — {{ r.resource_class }}/{{ r.form }}
          </option>
        </select>
      </div>
      <div v-if="selectedResource" class="field">
        <label class="field-label">Binding mode</label>
        <label v-for="m in allowedModes" :key="m" class="radio-row">
          <input v-model="bindForm.binding_mode" type="radio" :value="m" />
          <span>{{ m }}</span>
        </label>
        <span v-if="selectedResource.resource_class === 'compute' && selectedResource.form === 'logical'" class="field-hint">
          Logical compute services are always tenant-dedicated (exclusive).
        </span>
      </div>
      <div class="field">
        <label class="field-label">Purpose (optional)</label>
        <input v-model="bindForm.purpose" class="text-input" maxlength="200" placeholder="e.g. training pool" />
      </div>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="bindOpen = false">Cancel</button>
        <button class="btn btn-primary" type="button" @click="bind">Bind</button>
      </template>
    </ModalDialog>
  </div>
  <div v-else class="skeleton" style="height: 240px" />
</template>

<style scoped>
.profile-card,
.lifecycle-card {
  margin-bottom: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  align-items: flex-start;
}
.profile-head {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}
.field-block strong {
  display: inline-block;
  width: 160px;
  color: var(--color-steel);
  font-weight: 500;
}
.edit-actions,
.lifecycle-actions {
  display: flex;
  gap: var(--space-sm);
}
.radio-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  padding: 4px 0;
}
</style>
