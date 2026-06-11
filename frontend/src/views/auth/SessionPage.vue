<script setup lang="ts">
/** M01 UI page 3 — Session & tenant context, route /account/session:
 * session details, tenant memberships with role badges, expiry hint,
 * sign-out (FDD §2.1.2). */
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()

onMounted(() => {
  auth.loadCurrentSession()
})

const session = computed(() => auth.current?.session ?? null)

function fmt(ts: string | null | undefined): string {
  return ts ? new Date(ts).toLocaleString() : '—'
}

async function pickTenant(tenantId: string) {
  try {
    await auth.switchTenant(tenantId)
    toast.success('Active tenant switched.')
  } catch (e) {
    toast.apiError(e)
    await auth.loadCurrentSession()
  }
}

async function signOut() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div>
    <div class="page-header-row">
      <h1 class="text-display">Session</h1>
      <button class="btn btn-secondary" type="button" @click="signOut">Sign out</button>
    </div>

    <div v-if="!auth.current" class="skeleton" style="height: 180px" />
    <template v-else>
      <div class="card session-card">
        <div class="session-grid">
          <div>
            <p class="text-micro-upper">Signed in as</p>
            <p class="text-h5">{{ auth.user?.display_name }}</p>
            <p class="text-sm" style="color: var(--color-steel)">{{ auth.user?.email }}</p>
          </div>
          <div>
            <p class="text-micro-upper">Session</p>
            <p class="text-sm">Created {{ fmt(session?.created_at) }}</p>
            <p class="text-sm">
              Expires at {{ fmt(session?.absolute_expires_at) }} or after 60 min inactivity
            </p>
          </div>
        </div>
      </div>

      <h2 class="text-h4 section-title">Tenants</h2>
      <div v-if="auth.tenants.length === 0" class="empty-state card">
        No tenant assigned yet. Contact your platform administrator.
      </div>
      <div v-else class="tenant-list">
        <div v-for="t in auth.tenants" :key="t.tenant_id" class="card tenant-row">
          <div class="tenant-main">
            <p class="text-h5">{{ t.name }}</p>
            <div class="role-badges">
              <span v-for="r in t.roles" :key="r" class="tag-chip">{{ r }}</span>
              <span v-if="t.roles.length === 0" class="text-caption">membership via projects</span>
            </div>
            <p v-if="t.projects.length" class="text-caption">
              Projects: {{ t.projects.map((p) => p.name).join(', ') }}
            </p>
          </div>
          <div class="tenant-side">
            <span class="badge" :class="`badge-${t.status}`">{{ t.status }}</span>
            <button
              v-if="t.tenant_id !== auth.activeTenantId"
              class="btn btn-secondary btn-sm"
              type="button"
              :disabled="t.status !== 'active'"
              @click="pickTenant(t.tenant_id)"
            >
              Make active
            </button>
            <span v-else class="badge badge-purple">active context</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.session-card {
  margin-bottom: var(--space-xxl);
}
.session-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-xl);
}
@media (max-width: 767px) {
  .session-grid {
    grid-template-columns: 1fr;
  }
}
.section-title {
  margin-bottom: var(--space-md);
}
.tenant-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}
.tenant-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
}
.tenant-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.role-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.tenant-side {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex: none;
}
</style>
