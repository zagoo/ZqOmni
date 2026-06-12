<script setup lang="ts">
/** M03 UI page 6 — Audit explorer, /tenant/audit (TA/Governance) and
 * /admin/audit (PA; OE sees the server-enforced infra domain filter).
 * Keyset pagination via "Load more". */
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import SelectMenu from '@/components/SelectMenu.vue'
import { describeApiError, useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import {
  m03QueryAdminAuditEvents,
  m03QueryTenantAuditEvents,
  type AuditEventOut,
} from '@/views/iam/api'

const route = useRoute()
const toast = useToast()
const auth = useAuthStore()
const surface = (route.meta.scope as 'platform' | 'tenant') ?? 'tenant'

const events = ref<AuditEventOut[]>([])
const nextToken = ref<string | null>(null)
const loading = ref(false)
const expanded = ref<string | null>(null)
const windowError = ref('')

const filters = reactive({
  occurred_after: '',
  occurred_before: '',
  action: '',
  actor_id: '',
  subject_id: '',
  decision: '',
})

const DECISION_OPTIONS = [
  { value: '', label: 'all' },
  { value: 'allow', label: 'allow' },
  { value: 'deny', label: 'deny' },
  { value: 'n/a', label: 'n/a' },
]

function buildQuery(pageToken: string | null) {
  return {
    occurred_after: filters.occurred_after ? new Date(filters.occurred_after).toISOString() : null,
    occurred_before: filters.occurred_before ? new Date(filters.occurred_before).toISOString() : null,
    action: filters.action || null,
    actor_id: filters.actor_id || null,
    subject_id: filters.subject_id || null,
    decision: filters.decision || null,
    page_size: 50,
    page_token: pageToken,
  }
}

async function load(append = false) {
  loading.value = true
  windowError.value = ''
  try {
    const query = buildQuery(append ? nextToken.value : null)
    const result =
      surface === 'platform'
        ? await m03QueryAdminAuditEvents({ query, throwOnError: true })
        : await m03QueryTenantAuditEvents({
            path: { tenant_id: auth.activeTenantId ?? '' },
            query,
            throwOnError: true,
          })
    const page = result.data.data
    events.value = append ? [...events.value, ...(page?.items ?? [])] : (page?.items ?? [])
    nextToken.value = page?.next_page_token ?? null
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    if (errorCode === 'E_VALIDATION') windowError.value = message
    else toast.apiError(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <div>
    <h1 class="text-display page-title">Audit</h1>

    <div class="card filter-card">
      <div class="filter-grid">
        <div class="field">
          <label class="field-label">After</label>
          <input v-model="filters.occurred_after" class="text-input" type="datetime-local" />
        </div>
        <div class="field">
          <label class="field-label">Before</label>
          <input v-model="filters.occurred_before" class="text-input" type="datetime-local" />
        </div>
        <div class="field">
          <label class="field-label">Action prefix</label>
          <input v-model="filters.action" class="text-input" placeholder="e.g. iam.role_binding." />
        </div>
        <div class="field">
          <label class="field-label">Actor id</label>
          <input v-model="filters.actor_id" class="text-input" placeholder="usr-…" />
        </div>
        <div class="field">
          <label class="field-label">Subject id</label>
          <input v-model="filters.subject_id" class="text-input" placeholder="any asset id" />
        </div>
        <div class="field">
          <label class="field-label">Decision</label>
          <SelectMenu v-model="filters.decision" :options="DECISION_OPTIONS" />
        </div>
      </div>
      <p v-if="windowError" class="field-error">{{ windowError }}</p>
      <button class="btn btn-primary btn-sm" type="button" :disabled="loading" @click="load()">
        Apply filters
      </button>
    </div>

    <div v-if="loading && events.length === 0" class="skeleton" style="height: 280px" />
    <div v-else-if="events.length === 0" class="empty-state card">
      No audit events in this window.
    </div>
    <div v-else class="event-stream">
      <div
        v-for="e in events"
        :key="e.event_id"
        class="event-row"
        @click="expanded = expanded === e.event_id ? null : e.event_id"
      >
        <div class="event-main">
          <span class="text-caption event-time">{{ new Date(e.occurred_at).toLocaleString() }}</span>
          <code class="event-action">{{ e.action }}</code>
          <span class="tag-chip">{{ e.actor.type }}:{{ e.actor.id.slice(0, 16) }}</span>
          <span class="text-caption">→ {{ e.subject.type }}:{{ e.subject.id.slice(0, 20) }}</span>
          <span
            class="badge"
            :class="e.decision === 'deny' ? 'badge-error' : e.decision === 'allow' ? 'badge-active' : 'badge-neutral'"
          >
            {{ e.decision }}
          </span>
        </div>
        <div v-if="expanded === e.event_id" class="event-detail">
          <p class="text-caption">module {{ e.source_module }} · tenant {{ e.scope.tenant_id ?? '—' }} · project {{ e.scope.project_id ?? '—' }}<template v-if="e.reason"> · reason: {{ e.reason }}</template></p>
          <pre v-if="e.before_summary" class="event-json">before: {{ JSON.stringify(e.before_summary) }}</pre>
          <pre v-if="e.after_summary" class="event-json">after: {{ JSON.stringify(e.after_summary) }}</pre>
        </div>
      </div>
      <button
        v-if="nextToken"
        class="btn btn-secondary load-more"
        type="button"
        :disabled="loading"
        @click="load(true)"
      >
        {{ loading ? 'Loading…' : 'Load more' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  margin-bottom: var(--space-lg);
}
.filter-card {
  margin-bottom: var(--space-lg);
}
.filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 var(--space-md);
}
@media (max-width: 1023px) {
  .filter-grid {
    grid-template-columns: 1fr 1fr;
  }
}
.event-stream {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-hairline);
  border-radius: var(--rounded-md);
  background: var(--color-canvas);
  overflow: hidden;
}
.event-row {
  border-bottom: 1px solid var(--color-hairline-soft);
  padding: var(--space-sm) var(--space-md);
  cursor: pointer;
}
.event-row:last-of-type {
  border-bottom: none;
}
.event-main {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}
.event-time {
  width: 170px;
  flex: none;
}
.event-action {
  font-size: 13px;
  background: var(--color-surface);
  border-radius: var(--rounded-xs);
  padding: 2px 6px;
}
.event-detail {
  padding: var(--space-xs) 0 0 178px;
}
.event-json {
  font-size: 12px;
  color: var(--color-slate);
  background: var(--color-surface-soft);
  border-radius: var(--rounded-xs);
  padding: 6px 8px;
  margin: 4px 0 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.load-more {
  margin: var(--space-sm);
  align-self: center;
}
</style>
