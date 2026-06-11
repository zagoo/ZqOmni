<script setup lang="ts">
/** M03 UI page 2 — User detail & lifecycle, /admin/users/{user_id} (PA;
 * TA read-only). Includes M01 element 4 "Revoke all sessions". */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import ModalDialog from '@/components/ModalDialog.vue'
import { describeApiError, useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import {
  m01AdminRevokeUserSessions,
  m03DeactivateUser,
  m03DeleteRoleBinding,
  m03GetUser,
  m03ListRoleBindings,
  m03ReactivateUser,
  type RoleBindingOut,
  type UserOut,
} from '@/views/iam/api'

const route = useRoute()
const toast = useToast()
const auth = useAuthStore()
const userId = route.params.userId as string

const user = ref<UserOut | null>(null)
const bindings = ref<RoleBindingOut[]>([])
const loading = ref(true)

const canAdmin = computed(() => auth.can('iam.user:admin'))
const canRevoke = computed(() => auth.can('iam.user_session:delete'))

async function load() {
  loading.value = true
  try {
    const [u, b] = await Promise.all([
      m03GetUser({ path: { user_id: userId }, throwOnError: true }),
      m03ListRoleBindings({ query: { user_id: userId, page_size: 200 }, throwOnError: true }),
    ])
    user.value = u.data.data ?? null
    bindings.value = b.data.data?.items ?? []
  } catch (e) {
    toast.apiError(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const deactivateOpen = ref(false)
const deactivateReason = ref('')

async function deactivate() {
  try {
    await m03DeactivateUser({
      path: { user_id: userId },
      body: { reason: deactivateReason.value },
      throwOnError: true,
    })
    toast.success('User deactivated. All sessions revoked.')
    deactivateOpen.value = false
    await load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    toast.error(
      errorCode === 'E_IAM_LAST_PLATFORM_ADMIN'
        ? 'This is the last platform administrator. Assign another before deactivating.'
        : message,
    )
  }
}

async function reactivate() {
  try {
    await m03ReactivateUser({ path: { user_id: userId }, throwOnError: true })
    toast.success('User reactivated.')
    await load()
  } catch (e) {
    toast.apiError(e)
  }
}

const revokeOpen = ref(false)
async function revokeAll() {
  try {
    const { data } = await m01AdminRevokeUserSessions({
      path: { user_id: userId },
      throwOnError: true,
    })
    toast.success(`${data.data?.revoked_count ?? 0} session(s) revoked.`)
    revokeOpen.value = false
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    toast.error(
      errorCode === 'E_PERMISSION_DENIED'
        ? 'You do not have permission to revoke sessions.'
        : message,
    )
  }
}

async function removeBinding(binding: RoleBindingOut) {
  try {
    await m03DeleteRoleBinding({ path: { binding_id: binding.binding_id }, throwOnError: true })
    toast.success('Binding removed.')
    await load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    if (errorCode === 'E_IAM_LAST_PLATFORM_ADMIN') {
      toast.error('This is the last platform administrator binding.')
    } else if (errorCode === 'E_IAM_LAST_TENANT_ADMIN') {
      toast.error('This is the last tenant administrator binding of this tenant.')
    } else if (errorCode === 'E_VALIDATION') {
      toast.error('Manage via project membership.')
    } else {
      toast.error(message)
    }
  }
}
</script>

<template>
  <div>
    <div v-if="loading" class="skeleton" style="height: 220px" />
    <template v-else-if="user">
      <div class="page-header-row">
        <div>
          <h1 class="text-display">{{ user.display_name }}</h1>
          <p class="text-caption">{{ user.email }}</p>
        </div>
        <div class="header-actions">
          <button v-if="canRevoke" class="btn btn-secondary" type="button" @click="revokeOpen = true">
            Revoke all sessions
          </button>
          <button
            v-if="canAdmin && user.status !== 'deactivated'"
            class="btn btn-danger"
            type="button"
            @click="deactivateOpen = true"
          >
            Deactivate
          </button>
          <button
            v-if="canAdmin && user.status === 'deactivated'"
            class="btn btn-primary"
            type="button"
            @click="reactivate"
          >
            Reactivate
          </button>
        </div>
      </div>

      <div class="card profile-card">
        <span class="badge" :class="`badge-${user.status}`">{{ user.status }}</span>
        <p class="text-sm"><strong>Last login</strong> {{ user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'never' }}</p>
        <p class="text-sm"><strong>Created</strong> {{ new Date(user.created_at).toLocaleString() }}</p>
        <p v-if="user.deactivate_reason" class="text-sm"><strong>Deactivation reason</strong> {{ user.deactivate_reason }}</p>
        <p v-if="user.note" class="text-sm"><strong>Note</strong> {{ user.note }}</p>
      </div>

      <h2 class="text-h4 section-title">Role bindings</h2>
      <p v-if="user.status === 'deactivated'" class="banner-info">
        Bindings are kept but inert while the user is deactivated; reactivation restores prior
        access intact.
      </p>
      <div v-if="bindings.length === 0" class="empty-state card">No role bindings.</div>
      <table v-else class="data-table">
        <thead>
          <tr><th>Role</th><th>Scope</th><th>Origin</th><th>Granted</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="b in bindings" :key="b.binding_id">
            <td class="text-sm-medium">{{ b.role_name ?? b.role_id }}</td>
            <td>
              <span class="tag-chip">{{ b.scope.type }}{{ b.scope.id ? `:${b.scope.id}` : '' }}</span>
            </td>
            <td class="text-caption">{{ b.origin }}</td>
            <td class="text-caption">{{ new Date(b.created_at).toLocaleDateString() }}</td>
            <td>
              <button
                v-if="auth.can('iam.role_binding:create') && b.origin === 'direct'"
                class="btn btn-ghost btn-sm"
                type="button"
                @click="removeBinding(b)"
              >
                Remove
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <ModalDialog title="Deactivate user" :open="deactivateOpen" @close="deactivateOpen = false">
        <p class="banner-warning">
          Revokes all sessions and blocks login. Bindings are kept but inert.
        </p>
        <div class="field">
          <label class="field-label">Reason (10–500 chars)</label>
          <textarea v-model="deactivateReason" class="textarea-input" maxlength="500" />
        </div>
        <template #footer>
          <button class="btn btn-secondary" type="button" @click="deactivateOpen = false">Cancel</button>
          <button
            class="btn btn-danger"
            type="button"
            :disabled="deactivateReason.trim().length < 10"
            @click="deactivate"
          >
            Deactivate
          </button>
        </template>
      </ModalDialog>

      <ModalDialog title="Revoke all sessions" :open="revokeOpen" @close="revokeOpen = false">
        <p class="text-body">
          This signs {{ user.display_name }} out of every device. Continue?
        </p>
        <template #footer>
          <button class="btn btn-secondary" type="button" @click="revokeOpen = false">Cancel</button>
          <button class="btn btn-primary" type="button" @click="revokeAll">Revoke all</button>
        </template>
      </ModalDialog>
    </template>
    <div v-else class="empty-state card">User not found.</div>
  </div>
</template>

<style scoped>
.header-actions {
  display: flex;
  gap: var(--space-sm);
}
.profile-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  align-items: flex-start;
  margin-bottom: var(--space-xxl);
}
.profile-card strong {
  display: inline-block;
  width: 160px;
  color: var(--color-steel);
  font-weight: 500;
}
.section-title {
  margin-bottom: var(--space-md);
}
</style>
