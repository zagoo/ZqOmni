<script setup lang="ts">
/** M02 UI page 6 (part 2) — Project detail & members, /projects/{project_id}
 * (TA manage; RD read). Member upsert assigns persona templates (M02-10). */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import ModalDialog from '@/components/ModalDialog.vue'
import { describeApiError, useToast } from '@/composables/useToast'
import { useAuthStore } from '@/store/auth'
import {
  m02ArchiveProject,
  m02GetProject,
  m02LookupUsers,
  m02RemoveProjectMember,
  m02UpsertProjectMember,
  type ProjectOut,
} from '@/views/tenancy/api'
import { PERSONA_TEMPLATE_OPTIONS, useMemberList } from '@/views/tenancy/hooks/useTenancy'

const route = useRoute()
const toast = useToast()
const auth = useAuthStore()
const projectId = route.params.projectId as string

const project = ref<ProjectOut | null>(null)
const members = useMemberList(projectId)
const loading = ref(true)

const canManage = computed(() => auth.can('tenancy.project_member:update'))

onMounted(async () => {
  try {
    const { data } = await m02GetProject({ path: { project_id: projectId }, throwOnError: true })
    project.value = data.data ?? null
    await members.load()
  } catch (e) {
    toast.apiError(e)
  } finally {
    loading.value = false
  }
})

// --- Member editor ---
const editorOpen = ref(false)
const editorError = ref('')
const editor = reactive({ user_id: '', templates: new Set<string>(), note: '' })
const userOptions = ref<{ value: string; label: string }[]>([])

async function openEditor(userId?: string, templates?: string[]) {
  editorError.value = ''
  editor.user_id = userId ?? ''
  editor.templates = new Set(templates ?? [])
  editorOpen.value = true
  try {
    const { data } = await m02LookupUsers({ query: { page_size: 200 }, throwOnError: true })
    userOptions.value = (data.data?.items ?? [])
      .filter((u) => u.status !== 'deactivated')
      .map((u) => ({ value: u.user_id, label: `${u.display_name} (${u.email})` }))
  } catch (e) {
    toast.apiError(e)
  }
}

function toggleTemplate(key: string) {
  editor.templates.has(key) ? editor.templates.delete(key) : editor.templates.add(key)
}

async function saveMember() {
  if (!editor.user_id) {
    editorError.value = 'Select a user.'
    return
  }
  if (editor.templates.size === 0) {
    editorError.value = 'Select at least one persona template.'
    return
  }
  try {
    await m02UpsertProjectMember({
      path: { project_id: projectId, user_id: editor.user_id },
      body: { persona_templates: [...editor.templates], note: editor.note || null },
      throwOnError: true,
    })
    toast.success('Member saved. Permissions take effect within a few seconds.')
    editorOpen.value = false
    await members.load()
  } catch (e) {
    editorError.value = describeApiError(e).message
  }
}

async function removeMember(userId: string) {
  try {
    await m02RemoveProjectMember({
      path: { project_id: projectId, user_id: userId },
      throwOnError: true,
    })
    toast.success('Member removed.')
    await members.load()
  } catch (e) {
    toast.apiError(e)
  }
}

async function archiveProject() {
  try {
    const { data } = await m02ArchiveProject({ path: { project_id: projectId }, throwOnError: true })
    project.value = data.data ?? project.value
    toast.success('Project archived.')
  } catch (e) {
    const { errorCode, message } = describeApiError(e)
    toast.error(
      errorCode === 'E_TNT_PROJECT_ACTIVE_WORK'
        ? 'Running workflows block archiving. Drain them first.'
        : message,
    )
  }
}
</script>

<template>
  <div>
    <div v-if="loading" class="skeleton" style="height: 200px" />
    <template v-else-if="project">
      <div v-if="project.status === 'archived'" class="banner-warning">
        This project is archived (read-only).
      </div>
      <div class="page-header-row">
        <div>
          <h1 class="text-display">{{ project.display_name }}</h1>
          <p class="text-caption">{{ project.name }} · owner {{ project.owner_user_id }}</p>
        </div>
        <button
          v-if="canManage && project.status === 'active'"
          class="btn btn-secondary"
          type="button"
          @click="archiveProject"
        >
          Archive project
        </button>
      </div>

      <p v-if="project.description" class="text-body description">{{ project.description }}</p>

      <div class="page-header-row">
        <h2 class="text-h4">Members</h2>
        <button
          v-if="canManage && project.status === 'active'"
          class="btn btn-primary btn-sm"
          type="button"
          @click="openEditor()"
        >
          Add member
        </button>
      </div>

      <div v-if="members.items.value.length === 0" class="empty-state card">No members yet.</div>
      <table v-else class="data-table">
        <thead>
          <tr><th>User</th><th>Persona templates</th><th>Added</th><th v-if="canManage"></th></tr>
        </thead>
        <tbody>
          <tr v-for="m in members.items.value" :key="m.user_id">
            <td>
              <span class="text-sm-medium">{{ m.display_name }}</span>
              <span class="text-caption block">{{ m.email }}</span>
            </td>
            <td>
              <span class="template-chips">
                <span v-for="t in m.persona_templates" :key="t" class="tag-chip">
                  {{ t.replace('persona.', '') }}
                </span>
              </span>
            </td>
            <td class="text-caption">{{ new Date(m.added_at).toLocaleDateString() }}</td>
            <td v-if="canManage">
              <span class="row-actions">
                <button
                  class="btn btn-ghost btn-sm"
                  type="button"
                  :disabled="project.status !== 'active'"
                  @click="openEditor(m.user_id, m.persona_templates)"
                >
                  Edit
                </button>
                <button
                  class="btn btn-ghost btn-sm"
                  type="button"
                  :disabled="project.status !== 'active'"
                  @click="removeMember(m.user_id)"
                >
                  Remove
                </button>
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <ModalDialog title="Project member" :open="editorOpen" @close="editorOpen = false">
        <p v-if="editorError" class="banner-error">{{ editorError }}</p>
        <div class="field">
          <label class="field-label">User</label>
          <select v-model="editor.user_id" class="select-input">
            <option value="" disabled>Add member…</option>
            <option v-for="o in userOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div class="field">
          <label class="field-label">Persona templates (≥1)</label>
          <label v-for="t in PERSONA_TEMPLATE_OPTIONS" :key="t" class="template-check">
            <input
              type="checkbox"
              :checked="editor.templates.has(t)"
              @change="toggleTemplate(t)"
            />
            <span>{{ t.replace('persona.', '').replace(/_/g, ' ') }}</span>
          </label>
        </div>
        <div class="field">
          <label class="field-label">Note (optional)</label>
          <input v-model="editor.note" class="text-input" maxlength="500" />
        </div>
        <template #footer>
          <button class="btn btn-secondary" type="button" @click="editorOpen = false">Cancel</button>
          <button class="btn btn-primary" type="button" @click="saveMember">Save member</button>
        </template>
      </ModalDialog>
    </template>
    <div v-else class="empty-state card">Project not found.</div>
  </div>
</template>

<style scoped>
.description {
  margin-bottom: var(--space-xl);
  color: var(--color-charcoal);
}
.block {
  display: block;
}
.template-chips {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.row-actions {
  display: flex;
  gap: 4px;
}
.template-check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  padding: 3px 0;
}
</style>
