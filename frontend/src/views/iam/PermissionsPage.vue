<script setup lang="ts">
/** M03 UI page 3 — Permission catalog explorer, /admin/permissions
 * (read-only; catalog transparency per BR-13). */
import { computed, onMounted } from 'vue'
import { watchDebounced } from '@vueuse/core'
import SelectMenu from '@/components/SelectMenu.vue'
import { usePermissionCatalog } from '@/views/iam/hooks/useIam'

const catalog = usePermissionCatalog()
onMounted(catalog.load)
watchDebounced([catalog.q, catalog.domain], catalog.load, { debounce: 300 })

const domains = computed(() => [...new Set(catalog.items.value.map((p) => p.domain))].sort())
const domainOptions = computed(() => [
  { value: '', label: 'All domains' },
  ...domains.value.map((d) => ({ value: d, label: d })),
])
</script>

<template>
  <div>
    <h1 class="text-display page-title">Permissions</h1>
    <p class="text-sm intro">
      Atomic permission units ({{ '{domain}.{resource}:{action}' }}); custom roles recombine
      them. The catalog is code-defined and read-only.
    </p>

    <div class="toolbar-row">
      <input v-model="catalog.q.value" class="search-pill filter-search" placeholder="Filter permissions…" />
      <SelectMenu v-model="catalog.domain.value" class="domain-select" :options="domainOptions" />
    </div>

    <div v-if="catalog.loading.value" class="skeleton" style="height: 280px" />
    <div v-else-if="catalog.items.value.length === 0" class="empty-state card">
      No permissions match the filters.
    </div>
    <table v-else class="data-table">
      <thead>
        <tr><th>Key</th><th>Description</th><th>Module</th><th>Scope levels</th></tr>
      </thead>
      <tbody>
        <tr v-for="p in catalog.items.value" :key="p.key">
          <td>
            <code class="perm-key">{{ p.key }}</code>
            <span v-if="p.service_only" class="badge badge-neutral service-badge">service</span>
          </td>
          <td class="text-sm">{{ p.description }}</td>
          <td><span class="tag-chip">{{ p.owning_module }}</span></td>
          <td class="text-caption">{{ p.scope_levels.join(', ') }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.page-title {
  margin-bottom: var(--space-xs);
}
.intro {
  color: var(--color-steel);
  margin-bottom: var(--space-lg);
}
.filter-search {
  max-width: 320px;
}
.domain-select {
  max-width: 220px;
}
.perm-key {
  font-size: 13px;
  background: var(--color-surface);
  border-radius: var(--rounded-xs);
  padding: 2px 6px;
}
.service-badge {
  margin-left: 6px;
}
</style>
