<script setup lang="ts">
/** M02 UI page 5 — Tenant self view, /tenant (TA, RD read): read-only
 * profile + sanitized bindings (no credentials, no vault paths). */
import { onMounted, ref } from 'vue'
import { describeApiError } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import {
  m02GetTenantSelf,
  m02ListTenantBindingsSelf,
  type BindingPublicOut,
  type TenantPublicOut,
} from '@/views/tenancy/api'

const auth = useAuthStore()
const tenant = ref<TenantPublicOut | null>(null)
const bindings = ref<BindingPublicOut[]>([])
const loading = ref(true)
const errorMessage = ref('')
const suspendedNotice = ref(false)

onMounted(async () => {
  const tid = auth.activeTenantId
  if (!tid) {
    errorMessage.value = 'No tenant assigned yet. Contact your platform administrator.'
    loading.value = false
    return
  }
  try {
    const [t, b] = await Promise.all([
      m02GetTenantSelf({ path: { tenant_id: tid }, throwOnError: true }),
      m02ListTenantBindingsSelf({ path: { tenant_id: tid }, throwOnError: true }),
    ])
    tenant.value = t.data.data ?? null
    bindings.value = b.data.data?.items ?? []
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    if (errorCode === 'E_TENANT_SUSPENDED') suspendedNotice.value = true
    else errorMessage.value = message
  } finally {
    loading.value = false
  }
})

function capacityLabel(view: Record<string, unknown>): string {
  return (
    Object.entries(view)
      .filter(([, v]) => v != null && v !== 0)
      .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`)
      .join(' · ') || '—'
  )
}
</script>

<template>
  <div>
    <h1 class="text-display page-title">My tenant</h1>

    <div v-if="loading" class="skeleton" style="height: 200px" />
    <div v-else-if="suspendedNotice" class="card empty-state">
      This tenant is suspended. Contact your platform administrator.
    </div>
    <div v-else-if="errorMessage" class="card empty-state">{{ errorMessage }}</div>
    <template v-else-if="tenant">
      <div class="card profile">
        <div class="profile-row">
          <h2 class="text-h4">{{ tenant.display_name }}</h2>
          <span class="badge" :class="`badge-${tenant.status}`">{{ tenant.status }}</span>
        </div>
        <p class="text-sm" style="color: var(--color-steel)">{{ tenant.description || 'No description.' }}</p>
        <p class="text-caption">
          Storage isolation: {{ tenant.settings?.storage_isolation }}
        </p>
      </div>

      <h2 class="text-h4 section-title">Bound resources</h2>
      <div v-if="bindings.length === 0" class="empty-state card">
        No resources bound yet. Contact your platform administrator.
      </div>
      <table v-else class="data-table">
        <thead>
          <tr><th>Resource</th><th>Kind</th><th>Mode</th><th>Capacity</th><th>Health</th></tr>
        </thead>
        <tbody>
          <tr v-for="b in bindings" :key="b.binding_id">
            <td class="text-sm-medium">{{ b.resource_name }}</td>
            <td>{{ b.resource_class }}/{{ b.form }}</td>
            <td>{{ b.binding_mode }}</td>
            <td class="text-caption">{{ capacityLabel(b.capacity_view) }}</td>
            <td>
              <span v-if="b.health" class="badge" :class="b.health === 'reachable' ? 'badge-active' : 'badge-warning'">
                {{ b.health }}
              </span>
              <span v-else class="text-caption">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<style scoped>
.page-title {
  margin-bottom: var(--space-xl);
}
.profile {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  margin-bottom: var(--space-xxl);
}
.profile-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}
.section-title {
  margin-bottom: var(--space-md);
}
</style>
