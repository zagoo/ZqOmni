<script setup lang="ts">
/** Resolves a binding/inspection scope id from human-readable selectors so
 * operators never have to know an opaque tnt-…/prj-… ulid. Platform scope
 * needs no id; tenant scope picks a tenant; project scope picks a tenant then
 * one of its projects. The tenant list comes from the admin endpoint on the
 * platform surface and from the caller's own memberships on the tenant
 * surface (which cannot read the platform-wide tenant list). */
import { ref, watch } from 'vue'
import DropdownRow from '@/components/DropdownRow.vue'
import { m02ListProjects, m02ListTenants } from '@/api/generated/sdk.gen'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'

const props = defineProps<{
  scopeType: 'platform' | 'tenant' | 'project'
  modelValue: string
  surface: 'platform' | 'tenant'
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const auth = useAuthStore()
const toast = useToast()

type Option = { value: string; label: string }
const tenantOptions = ref<Option[]>([])
const projectOptions = ref<Option[]>([])
const projectTenant = ref('') // tenant whose projects fill the project list
const loadingProjects = ref(false)

async function loadTenants() {
  if (props.surface === 'platform') {
    try {
      const { data } = await m02ListTenants({
        query: { status: ['active', 'suspended'], page_size: 200 },
        throwOnError: true,
      })
      tenantOptions.value = (data.data?.items ?? []).map((t) => ({
        value: t.tenant_id,
        label: `${t.name} · ${t.display_name}`,
      }))
    } catch (e) {
      toast.apiError(e)
    }
  } else {
    tenantOptions.value = auth.tenants.map((t) => ({ value: t.tenant_id, label: t.name }))
  }
}

async function loadProjects(tenantId: string) {
  if (!tenantId) {
    projectOptions.value = []
    return
  }
  loadingProjects.value = true
  try {
    const { data } = await m02ListProjects({
      path: { tenant_id: tenantId },
      query: { page_size: 200 },
      throwOnError: true,
    })
    projectOptions.value = (data.data?.items ?? []).map((p) => ({
      value: p.project_id,
      label: `${p.name} · ${p.display_name}`,
    }))
  } catch (e) {
    toast.apiError(e)
    projectOptions.value = []
  } finally {
    loadingProjects.value = false
  }
}

function selectTenant(id: string) {
  emit('update:modelValue', id)
}

function selectProjectTenant(id: string) {
  projectTenant.value = id
  emit('update:modelValue', '') // the project must be re-picked under the new tenant
  loadProjects(id)
}

function selectProject(id: string) {
  emit('update:modelValue', id)
}

/** Default tenant scope to the active tenant (preserves the prior "defaults to
 * the active tenant" affordance) once the options are loaded. */
function applyTenantDefault() {
  if (props.scopeType !== 'tenant' || props.modelValue) return
  const active = auth.activeTenantId
  if (active && tenantOptions.value.some((o) => o.value === active)) {
    emit('update:modelValue', active)
  }
}

function primeProjectScope() {
  if (!projectTenant.value) projectTenant.value = auth.activeTenantId ?? ''
  if (projectTenant.value) loadProjects(projectTenant.value)
}

// Clear stale ids and prime sensible defaults whenever the scope type changes.
watch(
  () => props.scopeType,
  (type) => {
    if (type === 'tenant') {
      if (props.modelValue && !props.modelValue.startsWith('tnt-')) emit('update:modelValue', '')
      applyTenantDefault()
    } else if (type === 'project') {
      if (props.modelValue && !props.modelValue.startsWith('prj-')) emit('update:modelValue', '')
      primeProjectScope()
    } else if (props.modelValue) {
      emit('update:modelValue', '')
    }
  },
)

watch(tenantOptions, applyTenantDefault)

loadTenants().then(() => {
  if (props.scopeType === 'project') primeProjectScope()
})
</script>

<template>
  <div class="scope-picker">
    <p v-if="props.scopeType === 'platform'" class="text-caption">
      Platform scope applies globally — no id required.
    </p>

    <DropdownRow
      v-else-if="props.scopeType === 'tenant'"
      :model-value="props.modelValue"
      label="Tenant"
      :options="tenantOptions"
      placeholder="Select tenant…"
      @update:model-value="selectTenant"
    />

    <template v-else>
      <DropdownRow
        :model-value="projectTenant"
        label="Tenant"
        :options="tenantOptions"
        placeholder="Select tenant…"
        @update:model-value="selectProjectTenant"
      />
      <DropdownRow
        :model-value="props.modelValue"
        label="Project"
        :options="projectOptions"
        :placeholder="
          loadingProjects
            ? 'Loading projects…'
            : projectTenant
              ? 'Select project…'
              : 'Select a tenant first'
        "
        :disabled="!projectTenant || loadingProjects"
        @update:model-value="selectProject"
      />
    </template>
  </div>
</template>

<style scoped>
.scope-picker {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}
</style>
