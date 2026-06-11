<script setup lang="ts">
/** M02 UI page 1 — Tenant administration list, /admin/tenants (PA). */
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { watchDebounced } from '@vueuse/core'
import ModalDialog from '@/components/ModalDialog.vue'
import { describeApiError, useToast } from '@/composables/useToast'
import { m02CreateTenant } from '@/views/tenancy/api'
import { useTenantList } from '@/views/tenancy/hooks/useTenancy'

const router = useRouter()
const toast = useToast()
const list = useTenantList()

onMounted(list.load)
watchDebounced(list.q, list.load, { debounce: 300 })

const createOpen = ref(false)
const creating = ref(false)
const form = reactive({
  name: '',
  display_name: '',
  description: '',
  storage_isolation: 'prefix_per_tenant' as 'prefix_per_tenant' | 'dedicated_bucket',
})
const formError = ref('')

const SLUG_RE = /^[a-z0-9][a-z0-9-]{2,38}$/

async function createTenant() {
  if (!SLUG_RE.test(form.name)) {
    formError.value = 'Lowercase letters, digits, hyphens; 3–39 chars.'
    return
  }
  if (!form.display_name.trim()) {
    formError.value = 'Display name is required.'
    return
  }
  creating.value = true
  try {
    await m02CreateTenant({
      body: {
        name: form.name,
        display_name: form.display_name.trim(),
        description: form.description.trim() || null,
        settings: { storage_isolation: form.storage_isolation },
      },
      throwOnError: true,
    })
    toast.success(`Tenant ${form.display_name} created.`)
    createOpen.value = false
    Object.assign(form, { name: '', display_name: '', description: '' })
    formError.value = ''
    await list.load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    formError.value =
      errorCode === 'E_CONFLICT' ? 'A tenant with this name already exists.' : message
  } finally {
    creating.value = false
  }
}

function toggleStatus(status: string) {
  const set = new Set(list.statuses.value)
  set.has(status) ? set.delete(status) : set.add(status)
  list.statuses.value = [...set]
  list.load()
}
</script>

<template>
  <div>
    <div class="page-header-row">
      <h1 class="text-display">Tenants</h1>
      <button class="btn btn-primary" type="button" @click="createOpen = true">New tenant</button>
    </div>

    <div class="toolbar-row">
      <input v-model="list.q.value" class="search-pill filter-search" placeholder="Search tenants…" />
      <button
        v-for="s in ['active', 'suspended', 'archived']"
        :key="s"
        class="filter-pill"
        :class="{ on: list.statuses.value.includes(s) }"
        type="button"
        @click="toggleStatus(s)"
      >
        {{ s }}
      </button>
    </div>

    <div v-if="list.loading.value" class="skeleton-stack">
      <div v-for="i in 8" :key="i" class="skeleton" style="height: 44px" />
    </div>
    <div v-else-if="list.items.value.length === 0" class="empty-state card">
      No tenants yet. Create the first tenant.
    </div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Display name</th>
          <th>Status</th>
          <th>Projects</th>
          <th>Bindings</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="t in list.items.value"
          :key="t.tenant_id"
          class="row-click"
          @click="router.push(`/admin/tenants/${t.tenant_id}`)"
        >
          <td class="text-sm-medium">{{ t.name }}</td>
          <td>{{ t.display_name }}</td>
          <td><span class="badge" :class="`badge-${t.status}`">{{ t.status }}</span></td>
          <td>{{ t.projects_count ?? '—' }}</td>
          <td>{{ t.bindings_count ?? '—' }}</td>
          <td class="text-caption">{{ new Date(t.created_at).toLocaleDateString() }}</td>
        </tr>
      </tbody>
    </table>

    <ModalDialog title="Create tenant" :open="createOpen" @close="createOpen = false">
      <p v-if="formError" class="banner-error">{{ formError }}</p>
      <div class="field">
        <label class="field-label">Name (slug)</label>
        <input v-model="form.name" class="text-input" placeholder="acme-robotics" />
        <span class="field-hint">Lowercase letters, digits, hyphens; 3–39 chars. Immutable.</span>
      </div>
      <div class="field">
        <label class="field-label">Display name</label>
        <input v-model="form.display_name" class="text-input" placeholder="Acme Robotics" maxlength="80" />
      </div>
      <div class="field">
        <label class="field-label">Description</label>
        <textarea v-model="form.description" class="textarea-input" maxlength="2000" placeholder="Purpose of this tenant" />
      </div>
      <div class="field">
        <label class="field-label">Storage isolation</label>
        <label class="radio-row">
          <input v-model="form.storage_isolation" type="radio" value="prefix_per_tenant" />
          <span>Prefix per tenant — shared object store with an enforced tenant prefix</span>
        </label>
        <label class="radio-row">
          <input v-model="form.storage_isolation" type="radio" value="dedicated_bucket" />
          <span>Dedicated bucket — premium isolation tier</span>
        </label>
      </div>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="createOpen = false">Cancel</button>
        <button class="btn btn-primary" type="button" :disabled="creating" @click="createTenant">
          {{ creating ? 'Creating…' : 'Create tenant' }}
        </button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.filter-search {
  max-width: 320px;
}
.filter-pill {
  border: 1px solid var(--color-hairline);
  background: transparent;
  color: var(--color-steel);
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  border-radius: var(--rounded-full);
  padding: 6px 14px;
  cursor: pointer;
}
.filter-pill.on {
  background: var(--color-ink-deep);
  border-color: var(--color-ink-deep);
  color: var(--color-on-dark);
}
.skeleton-stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}
.radio-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 14px;
  color: var(--color-charcoal);
  padding: 4px 0;
}
</style>
