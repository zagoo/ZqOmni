<script setup lang="ts">
/** M03 UI page 7 — Access reviews (RPT-11), /tenant/access-reviews. */
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import ModalDialog from '@/components/ModalDialog.vue'
import SelectMenu from '@/components/SelectMenu.vue'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import {
  m03CreateAccessReview,
  m03GetAccessReview,
  m03ListAccessReviewEntries,
  m03ListAccessReviews,
  type AccessReviewEntryOut,
  type AccessReviewOut,
} from '@/views/iam/api'

const toast = useToast()
const auth = useAuthStore()

const reviews = ref<AccessReviewOut[]>([])
const loading = ref(false)
const selected = ref<AccessReviewOut | null>(null)
const entries = ref<AccessReviewEntryOut[]>([])

async function load() {
  if (!auth.activeTenantId) return
  loading.value = true
  try {
    const { data } = await m03ListAccessReviews({
      path: { tenant_id: auth.activeTenantId },
      query: { page_size: 50 },
      throwOnError: true,
    })
    reviews.value = data.data?.items ?? []
  } catch (e) {
    toast.apiError(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

let poll: ReturnType<typeof setInterval> | null = null
onBeforeUnmount(() => poll && clearInterval(poll))

function watchGenerating(reviewId: string) {
  poll && clearInterval(poll)
  poll = setInterval(async () => {
    const { data } = await m03GetAccessReview({ path: { review_id: reviewId } })
    const review = data?.data
    if (review && review.status !== 'generating') {
      poll && clearInterval(poll)
      await load()
      if (selected.value?.review_id === reviewId) openReview(review)
    }
  }, 1500)
}

const createOpen = ref(false)
const form = reactive({
  review_type: 'combined' as 'restricted_datasets' | 'release_artifacts' | 'combined',
})

const REVIEW_TYPE_OPTIONS = [
  { value: 'restricted_datasets', label: 'Restricted datasets' },
  { value: 'release_artifacts', label: 'Release artifacts' },
  { value: 'combined', label: 'Combined' },
]

async function createReview() {
  if (!auth.activeTenantId) return
  try {
    const { data } = await m03CreateAccessReview({
      path: { tenant_id: auth.activeTenantId },
      body: { review_type: form.review_type },
      throwOnError: true,
    })
    toast.success('Review generation started.')
    createOpen.value = false
    await load()
    if (data.data) watchGenerating(data.data.review_id)
  } catch (e) {
    toast.apiError(e)
  }
}

async function openReview(review: AccessReviewOut) {
  selected.value = review
  entries.value = []
  if (review.status !== 'ready') return
  try {
    const { data } = await m03ListAccessReviewEntries({
      path: { review_id: review.review_id },
      query: { page_size: 500 },
      throwOnError: true,
    })
    entries.value = data.data?.items ?? []
  } catch (e) {
    toast.apiError(e)
  }
}
</script>

<template>
  <div>
    <div class="page-header-row">
      <h1 class="text-display">Access reviews</h1>
      <button
        v-if="auth.can('iam.access_review:create')"
        class="btn btn-primary"
        type="button"
        @click="createOpen = true"
      >
        New review
      </button>
    </div>
    <p class="text-sm intro">
      Periodic governance reports over restricted-data and release-artifact access (RPT-11).
      Entries derive from role bindings, persona templates, and the audit trail.
    </p>

    <div v-if="!auth.activeTenantId" class="empty-state card">
      Select an active tenant to view its access reviews.
    </div>
    <template v-else>
      <div v-if="loading" class="skeleton" style="height: 160px" />
      <div v-else-if="reviews.length === 0" class="empty-state card">No reviews yet.</div>
      <table v-else class="data-table">
        <thead>
          <tr><th>Review</th><th>Type</th><th>Status</th><th>Period</th><th>Summary</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in reviews" :key="r.review_id" class="row-click" @click="openReview(r)">
            <td class="text-caption">{{ r.review_id.slice(0, 18) }}…</td>
            <td>{{ r.review_type }}</td>
            <td>
              <span
                class="badge"
                :class="r.status === 'ready' ? 'badge-active' : r.status === 'failed' ? 'badge-error' : 'badge-info'"
              >
                {{ r.status }}
              </span>
            </td>
            <td class="text-caption">
              {{ new Date(r.period_start).toLocaleDateString() }} –
              {{ new Date(r.period_end).toLocaleDateString() }}
            </td>
            <td class="text-caption">
              <template v-if="r.summary">
                {{ r.summary.dormant_grants }} dormant · {{ r.summary.anomalies }} anomalies
              </template>
              <template v-else-if="r.status === 'failed'">Generation failed. Retry.</template>
              <template v-else>generating…</template>
            </td>
          </tr>
        </tbody>
      </table>

      <template v-if="selected && selected.status === 'ready'">
        <h2 class="text-h4 entries-title">Entries — {{ selected.review_id.slice(0, 18) }}…</h2>
        <div v-if="entries.length === 0" class="empty-state card">
          No grant entries in this period.
        </div>
        <table v-else class="data-table">
          <thead>
            <tr><th>User</th><th>Grant</th><th>Last access</th><th>Anomalies</th></tr>
          </thead>
          <tbody>
            <tr v-for="(e, i) in entries" :key="i">
              <td class="text-sm-medium">{{ e.display_name }}</td>
              <td class="text-caption">
                {{ (e.grant as any).role }} @ {{ (e.grant as any).scope }} · granted by
                {{ (e.grant as any).granted_by ?? '—' }}
              </td>
              <td class="text-caption">
                {{ e.last_access_at ? new Date(e.last_access_at).toLocaleString() : 'no activity' }}
              </td>
              <td>
                <span v-for="a in e.anomalies" :key="a" class="badge badge-warning anomaly">{{ a }}</span>
                <span v-if="e.anomalies.length === 0" class="text-caption">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
    </template>

    <ModalDialog title="New access review" :open="createOpen" @close="createOpen = false">
      <div class="field">
        <label class="field-label">Review type</label>
        <SelectMenu v-model="form.review_type" :options="REVIEW_TYPE_OPTIONS" />
        <span class="field-hint">Period defaults to the last 90 days.</span>
      </div>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="createOpen = false">Cancel</button>
        <button class="btn btn-primary" type="button" @click="createReview">Generate</button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.intro {
  color: var(--color-steel);
  margin-bottom: var(--space-lg);
}
.entries-title {
  margin: var(--space-xl) 0 var(--space-md);
}
.anomaly {
  margin-right: 4px;
}
</style>
