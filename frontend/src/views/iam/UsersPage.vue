<script setup lang="ts">
/** M03 UI page 1 — User directory & pre-registration, /admin/users (PA). */
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { watchDebounced } from '@vueuse/core'
import ModalDialog from '@/components/ModalDialog.vue'
import { describeApiError, useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import { m03PreregisterUser } from '@/views/iam/api'
import { useUserList } from '@/views/iam/hooks/useIam'

const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const list = useUserList()

onMounted(list.load)
watchDebounced(list.q, list.load, { debounce: 300 })

const createOpen = ref(false)
const creating = ref(false)
const formError = ref('')
const form = reactive({ email: '', display_name: '', note: '' })

async function preregister() {
  if (!form.email.trim() || !form.display_name.trim()) {
    formError.value = 'Email and display name are required.'
    return
  }
  creating.value = true
  try {
    await m03PreregisterUser({
      body: {
        email: form.email.trim().toLowerCase(),
        display_name: form.display_name.trim(),
        note: form.note.trim() || null,
      },
      throwOnError: true,
    })
    toast.success('User invited. They can now request a login code.')
    createOpen.value = false
    Object.assign(form, { email: '', display_name: '', note: '' })
    formError.value = ''
    await list.load()
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    formError.value =
      errorCode === 'E_IAM_EMAIL_EXISTS' ? 'This email is already registered.' : message
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
      <h1 class="text-display">Users</h1>
      <button
        v-if="auth.can('iam.user:create')"
        class="btn btn-primary"
        type="button"
        @click="createOpen = true"
      >
        Pre-register user
      </button>
    </div>

    <div class="toolbar-row">
      <input v-model="list.q.value" class="search-pill filter-search" placeholder="Search users…" />
      <button
        v-for="s in ['invited', 'active', 'deactivated']"
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
    <div v-else-if="list.items.value.length === 0" class="empty-state card">No users match.</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Name</th><th>Email</th><th>Status</th><th>Last login</th><th>Bindings</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="u in list.items.value"
          :key="u.user_id"
          class="row-click"
          @click="router.push(`/admin/users/${u.user_id}`)"
        >
          <td class="text-sm-medium">{{ u.display_name }}</td>
          <td>{{ u.email }}</td>
          <td><span class="badge" :class="`badge-${u.status}`">{{ u.status }}</span></td>
          <td class="text-caption">
            {{ u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'never' }}
          </td>
          <td>{{ u.bindings_count ?? 0 }}</td>
        </tr>
      </tbody>
    </table>

    <ModalDialog title="Pre-register user" :open="createOpen" @close="createOpen = false">
      <p v-if="formError" class="banner-error">{{ formError }}</p>
      <div class="field">
        <label class="field-label">Corporate email</label>
        <input v-model="form.email" class="text-input" type="email" placeholder="name@company.com" maxlength="254" />
        <span class="field-hint">
          Pre-registration is the login prerequisite — only registered emails receive codes.
        </span>
      </div>
      <div class="field">
        <label class="field-label">Display name</label>
        <input v-model="form.display_name" class="text-input" maxlength="80" placeholder="Jane Doe" />
      </div>
      <div class="field">
        <label class="field-label">Note (optional)</label>
        <textarea v-model="form.note" class="textarea-input" maxlength="500" placeholder="Team / purpose" />
      </div>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="createOpen = false">Cancel</button>
        <button class="btn btn-primary" type="button" :disabled="creating" @click="preregister">
          {{ creating ? 'Inviting…' : 'Invite user' }}
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
</style>
