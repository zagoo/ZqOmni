<script setup lang="ts">
/** M02 UI page 3 — Resource inventory, /admin/resources (PA, OE):
 * 2-step register wizard (kind quadrant -> kind-specific descriptor). */
import { computed, onMounted, reactive, ref } from 'vue'
import ModalDialog from '@/components/ModalDialog.vue'
import { describeApiError, useToast } from '@/composables/useToast'
import {
  m02DecommissionResource,
  m02RegisterResource,
  type ResourceCreate,
} from '@/views/tenancy/api'
import { useResourceList } from '@/views/tenancy/hooks/useTenancy'

const toast = useToast()
const list = useResourceList()
onMounted(list.load)

const QUADRANTS = [
  { rclass: 'compute', form: 'physical', label: 'Physical compute', hint: 'GPU machine' },
  { rclass: 'compute', form: 'logical', label: 'Logical compute', hint: 'e.g. Ray cluster' },
  { rclass: 'storage', form: 'physical', label: 'Physical storage', hint: 'Volume / filesystem' },
  { rclass: 'storage', form: 'logical', label: 'Logical storage', hint: 'Object storage service' },
] as const

const wizardOpen = ref(false)
const step = ref<1 | 2>(1)
const kind = ref<(typeof QUADRANTS)[number] | null>(null)
const wizardError = ref('')
const saving = ref(false)

const form = reactive({
  name: '',
  hostname: '',
  gpu_model: 'H100',
  gpu_count: 8,
  cpu_cores: 96,
  memory_gib: 1024,
  service_type: 'ray_cluster',
  endpoint_url: '',
  cap_gpu: 0,
  cap_cpu: 0,
  cap_mem: 0,
  cap_workers: 0,
  volume_ref: '',
  filesystem: 'xfs',
  capacity_gib: 1024,
  export_path: '',
  bucket: '',
  region: '',
  access_key_id: '',
  secret: '',
})

function openWizard() {
  step.value = 1
  kind.value = null
  wizardError.value = ''
  wizardOpen.value = true
}

function pickKind(q: (typeof QUADRANTS)[number]) {
  kind.value = q
  form.service_type = q.rclass === 'compute' ? 'ray_cluster' : 'object_storage'
  step.value = 2
}

const isLogical = computed(() => kind.value?.form === 'logical')

function buildPayload(): ResourceCreate | null {
  if (!kind.value) return null
  const k = kind.value
  const descriptor: ResourceCreate['descriptor'] = {}
  if (k.rclass === 'compute' && k.form === 'physical') {
    descriptor.compute_physical = {
      hostname: form.hostname,
      gpu_model: form.gpu_model,
      gpu_count: form.gpu_count,
      cpu_cores: form.cpu_cores,
      memory_gib: form.memory_gib,
    }
  } else if (k.rclass === 'compute' && k.form === 'logical') {
    descriptor.compute_logical = {
      service_type: 'ray_cluster',
      endpoint_url: form.endpoint_url,
      capacity: {
        gpu_count: form.cap_gpu,
        cpu_cores: form.cap_cpu,
        memory_gib: form.cap_mem,
        max_workers: form.cap_workers,
      },
    }
  } else if (k.rclass === 'storage' && k.form === 'physical') {
    descriptor.storage_physical = {
      volume_ref: form.volume_ref,
      filesystem: form.filesystem,
      capacity_gib: form.capacity_gib,
      export_path: form.export_path,
    }
  } else {
    descriptor.storage_logical = {
      service_type: 'object_storage',
      endpoint_url: form.endpoint_url,
      bucket: form.bucket,
      region: form.region || null,
    }
  }
  return {
    name: form.name,
    resource_class: k.rclass,
    form: k.form,
    descriptor,
    credential: isLogical.value
      ? { access_key_id: form.access_key_id || null, secret: form.secret || null }
      : null,
  }
}

async function register() {
  const payload = buildPayload()
  if (!payload || !payload.name.trim()) {
    wizardError.value = 'Name is required.'
    return
  }
  saving.value = true
  try {
    await m02RegisterResource({ body: payload, throwOnError: true })
    toast.success(`Resource ${payload.name} registered.`)
    wizardOpen.value = false
    await list.load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    wizardError.value =
      errorCode === 'E_TNT_CREDENTIAL_INVALID'
        ? 'Endpoint or credential rejected. The platform brokers existing services; verify the service is provisioned and reachable (it is not created by the platform).'
        : message
  } finally {
    saving.value = false
  }
}

async function decommission(resourceId: string) {
  try {
    await m02DecommissionResource({ path: { resource_id: resourceId }, throwOnError: true })
    toast.success('Resource decommissioned.')
    await list.load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    toast.error(
      errorCode === 'E_TNT_RESOURCE_IN_USE' ? 'Release these bindings first.' : message,
    )
  }
}
</script>

<template>
  <div>
    <div class="page-header-row">
      <h1 class="text-display">Resources</h1>
      <button class="btn btn-primary" type="button" @click="openWizard">Register resource</button>
    </div>
    <p class="text-sm intro-note">
      Inventory of externally provisioned equipment and services — the platform brokers and
      accounts; it does not provision hardware.
    </p>

    <div v-if="list.loading.value" class="card-grid">
      <div v-for="i in 4" :key="i" class="skeleton" style="height: 120px" />
    </div>
    <div v-else-if="list.items.value.length === 0" class="empty-state card">
      No resources registered yet.
    </div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Name</th><th>Kind</th><th>Status</th><th>Health</th><th>Bindings</th><th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in list.items.value" :key="r.resource_id">
          <td class="text-sm-medium">{{ r.name }}</td>
          <td>{{ r.resource_class }}/{{ r.form }}</td>
          <td><span class="badge" :class="r.status === 'active' ? 'badge-active' : 'badge-neutral'">{{ r.status }}</span></td>
          <td>
            <span v-if="r.health" class="badge" :class="r.health === 'reachable' ? 'badge-active' : 'badge-warning'">
              {{ r.health }}
            </span>
            <span v-else class="text-caption">—</span>
          </td>
          <td>{{ r.bindings_count ?? 0 }}</td>
          <td>
            <button
              v-if="r.status === 'active'"
              class="btn btn-ghost btn-sm"
              type="button"
              @click="decommission(r.resource_id)"
            >
              Decommission
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <ModalDialog title="Register resource" :open="wizardOpen" wide @close="wizardOpen = false">
      <p v-if="wizardError" class="banner-error">{{ wizardError }}</p>

      <!-- Step 1: kind quadrant -->
      <div v-if="step === 1" class="quadrant-grid">
        <button
          v-for="q in QUADRANTS"
          :key="q.label"
          class="quadrant"
          type="button"
          @click="pickKind(q)"
        >
          <span class="text-sm-medium">{{ q.label }}</span>
          <span class="text-caption">{{ q.hint }}</span>
        </button>
      </div>

      <!-- Step 2: kind-specific descriptor -->
      <template v-else-if="kind">
        <p class="text-caption step-back">
          <a href="#" @click.prevent="step = 1">← Change kind</a> · {{ kind.label }}
        </p>
        <div class="field">
          <label class="field-label">Name</label>
          <input v-model="form.name" class="text-input" maxlength="80" placeholder="gpu-node-a17" />
        </div>

        <template v-if="kind.rclass === 'compute' && kind.form === 'physical'">
          <div class="field"><label class="field-label">Hostname</label>
            <input v-model="form.hostname" class="text-input" placeholder="node-a17.dc1.local" /></div>
          <div class="grid-2">
            <div class="field"><label class="field-label">GPU model</label>
              <input v-model="form.gpu_model" class="text-input" /></div>
            <div class="field"><label class="field-label">GPU count</label>
              <input v-model.number="form.gpu_count" class="text-input" type="number" min="1" max="16" /></div>
            <div class="field"><label class="field-label">CPU cores</label>
              <input v-model.number="form.cpu_cores" class="text-input" type="number" min="1" /></div>
            <div class="field"><label class="field-label">Memory (GiB)</label>
              <input v-model.number="form.memory_gib" class="text-input" type="number" min="1" /></div>
          </div>
        </template>

        <template v-else-if="kind.rclass === 'compute' && kind.form === 'logical'">
          <div class="field"><label class="field-label">Endpoint URL</label>
            <input v-model="form.endpoint_url" class="text-input" placeholder="https://ray-head.acme.svc:8265" /></div>
          <div class="grid-2">
            <div class="field"><label class="field-label">Capacity GPUs</label>
              <input v-model.number="form.cap_gpu" class="text-input" type="number" min="0" /></div>
            <div class="field"><label class="field-label">Capacity CPUs</label>
              <input v-model.number="form.cap_cpu" class="text-input" type="number" min="0" /></div>
            <div class="field"><label class="field-label">Memory (GiB)</label>
              <input v-model.number="form.cap_mem" class="text-input" type="number" min="0" /></div>
            <div class="field"><label class="field-label">Max workers</label>
              <input v-model.number="form.cap_workers" class="text-input" type="number" min="0" /></div>
          </div>
        </template>

        <template v-else-if="kind.rclass === 'storage' && kind.form === 'physical'">
          <div class="grid-2">
            <div class="field"><label class="field-label">Volume ref</label>
              <input v-model="form.volume_ref" class="text-input" placeholder="san-vol-009" /></div>
            <div class="field"><label class="field-label">Filesystem</label>
              <input v-model="form.filesystem" class="text-input" /></div>
            <div class="field"><label class="field-label">Capacity (GiB)</label>
              <input v-model.number="form.capacity_gib" class="text-input" type="number" min="1" /></div>
            <div class="field"><label class="field-label">Export path</label>
              <input v-model="form.export_path" class="text-input" placeholder="/exports/robodata1" /></div>
          </div>
        </template>

        <template v-else>
          <div class="field"><label class="field-label">Endpoint URL</label>
            <input v-model="form.endpoint_url" class="text-input" placeholder="https://s3.dc1.local" /></div>
          <div class="grid-2">
            <div class="field"><label class="field-label">Bucket</label>
              <input v-model="form.bucket" class="text-input" placeholder="platform-data" /></div>
            <div class="field"><label class="field-label">Region</label>
              <input v-model="form.region" class="text-input" placeholder="dc1" /></div>
          </div>
        </template>

        <template v-if="isLogical">
          <div class="grid-2">
            <div class="field"><label class="field-label">Access key id</label>
              <input v-model="form.access_key_id" class="text-input" autocomplete="off" /></div>
            <div class="field"><label class="field-label">Secret</label>
              <input v-model="form.secret" class="text-input" type="password" autocomplete="new-password" /></div>
          </div>
          <p class="field-hint">Credentials are write-only and stored in the platform vault; they are never echoed back.</p>
        </template>
      </template>

      <template #footer>
        <button class="btn btn-secondary" type="button" @click="wizardOpen = false">Cancel</button>
        <button v-if="step === 2" class="btn btn-primary" type="button" :disabled="saving" @click="register">
          {{ saving ? 'Registering…' : 'Register' }}
        </button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.intro-note {
  color: var(--color-steel);
  margin-bottom: var(--space-lg);
}
.quadrant-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-sm);
}
.quadrant {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  background: var(--color-canvas);
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-lg);
  padding: var(--space-lg);
  cursor: pointer;
  font-family: var(--font-sans);
}
.quadrant:active {
  border-color: var(--color-primary);
}
.step-back {
  margin-bottom: var(--space-sm);
}
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 var(--space-md);
}
</style>
