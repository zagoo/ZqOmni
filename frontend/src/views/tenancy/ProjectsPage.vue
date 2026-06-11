<script setup lang="ts">
/** M02 UI page 6 (part 1) — Projects, /tenant/projects (TA manage; RD read). */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import ContentCard from '@/components/ContentCard.vue'
import ModalDialog from '@/components/ModalDialog.vue'
import { describeApiError, useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import {
  m02CreateProject,
  m02ListTenantBindingsSelf,
  m02LookupUsers,
} from '@/views/tenancy/api'
import { useProjectList } from '@/views/tenancy/hooks/useTenancy'

const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const list = useProjectList(() => auth.activeTenantId)

onMounted(list.load)

const canManage = computed(() => auth.can('tenancy.project:create'))

const createOpen = ref(false)
const creating = ref(false)
const formError = ref('')
const form = reactive({ name: '', display_name: '', description: '', owner_user_id: '', default_storage_binding_id: '' })
const ownerOptions = ref<{ value: string; label: string }[]>([])
const storageOptions = ref<{ value: string; label: string }[]>([])

const SLUG_RE = /^[a-z0-9][a-z0-9-]{2,38}$/

async function openCreate() {
  formError.value = ''
  createOpen.value = true
  const tid = auth.activeTenantId
  if (!tid) return
  try {
    const [users, bindings] = await Promise.all([
      m02LookupUsers({ query: { page_size: 200 }, throwOnError: true }),
      m02ListTenantBindingsSelf({ path: { tenant_id: tid }, throwOnError: true }),
    ])
    ownerOptions.value = (users.data.data?.items ?? [])
      .filter((u) => u.status !== 'deactivated')
      .map((u) => ({ value: u.user_id, label: `${u.display_name} (${u.email})` }))
    storageOptions.value = (bindings.data.data?.items ?? [])
      .filter((b) => b.resource_class === 'storage' && b.status === 'active')
      .map((b) => ({ value: b.binding_id, label: b.resource_name }))
    if (storageOptions.value.length === 1) {
      form.default_storage_binding_id = storageOptions.value[0]!.value
    }
    if (!form.owner_user_id && auth.user) form.owner_user_id = auth.user.user_id
  } catch (e) {
    toast.apiError(e)
  }
}

async function createProject() {
  const tid = auth.activeTenantId
  if (!tid) return
  if (!SLUG_RE.test(form.name)) {
    formError.value = 'Project name: lowercase letters, digits, hyphens; 3–39 chars.'
    return
  }
  if (!form.display_name.trim() || !form.owner_user_id) {
    formError.value = 'Display name and owner are required.'
    return
  }
  if (storageOptions.value.length > 0 && !form.default_storage_binding_id) {
    formError.value = 'Select a default storage binding.'
    return
  }
  creating.value = true
  try {
    await m02CreateProject({
      path: { tenant_id: tid },
      body: {
        name: form.name,
        display_name: form.display_name.trim(),
        description: form.description.trim() || null,
        owner_user_id: form.owner_user_id,
        default_storage_binding_id: form.default_storage_binding_id || null,
      },
      throwOnError: true,
    })
    toast.success('Project created.')
    createOpen.value = false
    await list.load()
  } catch (e) {
    formError.value = describeApiError(e).message
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div>
    <div class="page-header-row">
      <h1 class="text-display">Projects</h1>
      <button v-if="canManage" class="btn btn-primary" type="button" @click="openCreate">
        New project
      </button>
    </div>

    <div v-if="!auth.activeTenantId" class="empty-state card">
      No tenant assigned yet. Contact your platform administrator.
    </div>
    <div v-else-if="list.loading.value" class="card-grid">
      <div v-for="i in 3" :key="i" class="skeleton" style="height: 140px" />
    </div>
    <div v-else-if="list.items.value.length === 0" class="empty-state card">
      No projects yet.
    </div>
    <div v-else class="card-grid">
      <ContentCard
        v-for="p in list.items.value"
        :key="p.project_id"
        icon="folder"
        :title="p.display_name"
        :description="p.description || p.name"
        :tint="p.status === 'archived' ? 'gray' : 'sky'"
        @click="router.push(`/projects/${p.project_id}`)"
      >
        <span class="card-footer-row">
          <span class="badge" :class="`badge-${p.status}`">{{ p.status }}</span>
          <span class="text-caption">{{ p.members_count ?? 0 }} member(s)</span>
        </span>
      </ContentCard>
    </div>

    <ModalDialog title="Create project" :open="createOpen" @close="createOpen = false">
      <p v-if="formError" class="banner-error">{{ formError }}</p>
      <div class="field">
        <label class="field-label">Name (slug)</label>
        <input v-model="form.name" class="text-input" placeholder="grasping-v2" />
      </div>
      <div class="field">
        <label class="field-label">Display name</label>
        <input v-model="form.display_name" class="text-input" maxlength="80" placeholder="Grasping v2" />
      </div>
      <div class="field">
        <label class="field-label">Description</label>
        <textarea v-model="form.description" class="textarea-input" maxlength="2000" />
      </div>
      <div class="field">
        <label class="field-label">Owner</label>
        <select v-model="form.owner_user_id" class="select-input">
          <option value="" disabled>Select owner…</option>
          <option v-for="o in ownerOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </div>
      <div class="field">
        <label class="field-label">Default storage binding</label>
        <select
          v-model="form.default_storage_binding_id"
          class="select-input"
          :disabled="storageOptions.length === 0"
        >
          <option value="" disabled>Select storage…</option>
          <option v-for="o in storageOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <span v-if="storageOptions.length === 0" class="field-hint">
          Bind storage to the tenant first.
        </span>
      </div>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="createOpen = false">Cancel</button>
        <button class="btn btn-primary" type="button" :disabled="creating" @click="createProject">
          {{ creating ? 'Creating…' : 'Create project' }}
        </button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.card-footer-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-top: var(--space-xs);
}
</style>
