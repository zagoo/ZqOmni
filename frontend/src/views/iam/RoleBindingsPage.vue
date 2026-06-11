<script setup lang="ts">
/** M03 UI page 5 — Role bindings + effective-permission inspector,
 * /admin/role-bindings and /tenant/role-bindings. The inspector lives in the
 * right configuration panel (AppShell panel slots). */
import { onMounted, reactive, ref } from "vue";
import DropdownRow from "@/components/DropdownRow.vue";
import ModalDialog from "@/components/ModalDialog.vue";
import SettingsSection from "@/components/SettingsSection.vue";
import { describeApiError, useToast } from "@/composables/useToast";
import { useAuthStore } from "@/store/auth";
import { useShellStore } from "@/store/shell";
import {
    m03CreateRoleBinding,
    m03DeleteRoleBinding,
    m03EffectivePermissions,
    type EffectivePermissionsResponse,
    type RoleBindingOut,
} from "@/views/iam/api";
import {
    BUILTIN_ROLE_OPTIONS,
    useBindingListQuery,
    useRoleList,
    useUserList,
} from "@/views/iam/hooks/useIam";

const toast = useToast();
const auth = useAuthStore();
const shell = useShellStore();

const bindings = useBindingListQuery();
const users = useUserList();
const roles = useRoleList(
    auth.can("tenancy.tenant:create") ? "platform" : "tenant",
);

onMounted(async () => {
    await Promise.all([bindings.load(), users.load(), roles.load()]);
});

// --- Create binding ---
const createOpen = ref(false);
const createError = ref("");
const form = reactive({
    user_id: "",
    role_id: "",
    scope_type: "tenant",
    scope_id: "",
});

async function createBinding() {
    if (!form.user_id || !form.role_id) {
        createError.value = "User and role are required.";
        return;
    }
    const scopeId =
        form.scope_type === "platform"
            ? null
            : form.scope_type === "tenant"
              ? form.scope_id || auth.activeTenantId
              : form.scope_id;
    if (form.scope_type !== "platform" && !scopeId) {
        createError.value = "Scope id is required for tenant/project scope.";
        return;
    }
    try {
        await m03CreateRoleBinding({
            body: {
                user_id: form.user_id,
                role_id: form.role_id,
                scope: {
                    type: form.scope_type as "platform" | "tenant" | "project",
                    id: scopeId,
                },
            },
            throwOnError: true,
        });
        toast.success("Binding created.");
        createOpen.value = false;
        await bindings.load();
    } catch (e) {
        const { errorCode, message } = describeApiError(e);
        createError.value =
            errorCode === "E_IAM_SCOPE_MISMATCH"
                ? "Scope id does not match the scope type."
                : errorCode === "E_PERMISSION_DENIED"
                  ? "You cannot grant a role exceeding your own effective permissions."
                  : message;
    }
}

async function removeBinding(b: RoleBindingOut) {
    try {
        await m03DeleteRoleBinding({
            path: { binding_id: b.binding_id },
            throwOnError: true,
        });
        toast.success("Binding removed.");
        await bindings.load();
    } catch (e) {
        const { errorCode, message } = describeApiError(e);
        if (errorCode === "E_IAM_LAST_PLATFORM_ADMIN") {
            toast.error("This is the last platform administrator binding.");
        } else if (errorCode === "E_IAM_LAST_TENANT_ADMIN") {
            toast.error(
                "This is the last tenant administrator binding of this tenant.",
            );
        } else if (errorCode === "E_VALIDATION") {
            toast.error("Manage via project membership.");
        } else {
            toast.error(message);
        }
    }
}

// --- Effective-permission inspector (right panel) ---
const inspector = reactive({ user_id: "", scope_type: "tenant", scope_id: "" });
const inspectorResult = ref<EffectivePermissionsResponse | null>(null);
const inspecting = ref(false);

function openInspector(userId?: string) {
    if (userId) inspector.user_id = userId;
    if (!inspector.scope_id && auth.activeTenantId)
        inspector.scope_id = auth.activeTenantId;
    shell.openPanel();
}

async function runInspection() {
    if (!inspector.user_id) return;
    inspecting.value = true;
    inspectorResult.value = null;
    try {
        const { data } = await m03EffectivePermissions({
            path: { user_id: inspector.user_id },
            query: {
                scope_type: inspector.scope_type,
                scope_id:
                    inspector.scope_type === "platform"
                        ? null
                        : inspector.scope_id || null,
            },
            throwOnError: true,
        });
        inspectorResult.value = data.data ?? null;
    } catch (e) {
        toast.apiError(e);
    } finally {
        inspecting.value = false;
    }
}
</script>

<template>
    <div>
        <div class="page-header-row">
            <h1 class="text-display">Role bindings</h1>
            <div class="header-actions">
                <button
                    class="btn btn-secondary"
                    type="button"
                    @click="openInspector()"
                >
                    Effective permissions
                </button>
                <button
                    v-if="auth.can('iam.role_binding:create')"
                    class="btn btn-primary"
                    type="button"
                    @click="createOpen = true"
                >
                    New binding
                </button>
            </div>
        </div>

        <div
            v-if="bindings.loading.value"
            class="skeleton"
            style="height: 280px"
        />
        <div
            v-else-if="bindings.items.value.length === 0"
            class="empty-state card"
        >
            No role bindings visible at this scope.
        </div>
        <table v-else class="data-table">
            <thead>
                <tr>
                    <th>User</th>
                    <th>Role</th>
                    <th>Scope</th>
                    <th>Origin</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="b in bindings.items.value" :key="b.binding_id">
                    <td class="text-sm-medium">
                        {{ b.user_display_name ?? b.user_id }}
                    </td>
                    <td>{{ b.role_name ?? b.role_id }}</td>
                    <td>
                        <span class="tag-chip"
                            >{{ b.scope.type
                            }}{{ b.scope.id ? `:${b.scope.id}` : "" }}</span
                        >
                    </td>
                    <td class="text-caption">{{ b.origin }}</td>
                    <td>
                        <span class="row-actions">
                            <button
                                class="btn btn-ghost btn-sm"
                                type="button"
                                @click="openInspector(b.user_id)"
                            >
                                Inspect
                            </button>
                            <button
                                v-if="
                                    auth.can('iam.role_binding:delete') &&
                                    b.origin === 'direct'
                                "
                                class="btn btn-ghost btn-sm"
                                type="button"
                                @click="removeBinding(b)"
                            >
                                Remove
                            </button>
                        </span>
                    </td>
                </tr>
            </tbody>
        </table>

        <!-- Inspector content mounts into the AppShell right panel -->
        <Teleport v-if="shell.panelOpen" to="#shell-panel-body">
            <div>
                <SettingsSection title="Effective permissions">
                    <DropdownRow
                        v-model="inspector.user_id"
                        label="User"
                        :options="
                            users.items.value.map((u) => ({
                                value: u.user_id,
                                label: u.display_name,
                            }))
                        "
                        placeholder="Select user…"
                    />
                    <DropdownRow
                        v-model="inspector.scope_type"
                        label="Scope type"
                        :options="[
                            { value: 'platform', label: 'platform' },
                            { value: 'tenant', label: 'tenant' },
                            { value: 'project', label: 'project' },
                        ]"
                    />
                    <div
                        v-if="inspector.scope_type !== 'platform'"
                        class="field"
                    >
                        <label class="field-label">Scope id</label>
                        <input
                            v-model="inspector.scope_id"
                            class="text-input"
                            placeholder="tnt-… / prj-…"
                        />
                    </div>
                    <button
                        class="btn btn-primary btn-sm"
                        type="button"
                        :disabled="inspecting"
                        @click="runInspection"
                    >
                        {{ inspecting ? "Resolving…" : "Resolve" }}
                    </button>
                </SettingsSection>

                <SettingsSection v-if="inspectorResult" title="Result">
                    <p class="text-caption">
                        user {{ inspectorResult.user_status }} · scope
                        {{ inspectorResult.scope_status }}
                        <template v-if="inspectorResult.denied_reasons.length">
                            · denied:
                            {{ inspectorResult.denied_reasons.join(", ") }}
                        </template>
                    </p>
                    <div
                        v-if="inspectorResult.allowed.length === 0"
                        class="text-caption"
                    >
                        No permissions at this scope.
                    </div>
                    <div
                        v-for="entry in inspectorResult.allowed"
                        :key="entry.key"
                        class="perm-row"
                    >
                        <code class="perm-key">{{ entry.key }}</code>
                        <span
                            class="text-caption"
                            :title="
                                entry.via
                                    .map((v) => `via ${v.role} @ ${v.scope}`)
                                    .join('\n')
                            "
                        >
                            via {{ entry.via[0]?.role }} @
                            {{ entry.via[0]?.scope }}
                        </span>
                    </div>
                </SettingsSection>
            </div>
        </Teleport>

        <ModalDialog
            title="New role binding"
            :open="createOpen"
            @close="createOpen = false"
        >
            <p v-if="createError" class="banner-error">{{ createError }}</p>
            <DropdownRow
                v-model="form.user_id"
                label="User"
                :options="
                    users.items.value.map((u) => ({
                        value: u.user_id,
                        label: `${u.display_name} (${u.email})`,
                    }))
                "
                placeholder="Select user…"
            />
            <DropdownRow
                v-model="form.role_id"
                label="Role"
                :options="[
                    ...BUILTIN_ROLE_OPTIONS,
                    ...roles.items.value
                        .filter((r) => r.role_type === 'custom')
                        .map((r) => ({
                            value: r.role_id,
                            label: `${r.name} (custom)`,
                        })),
                ]"
                placeholder="Select role…"
            />
            <DropdownRow
                v-model="form.scope_type"
                label="Scope type"
                :options="[
                    { value: 'platform', label: 'platform' },
                    { value: 'tenant', label: 'tenant' },
                    { value: 'project', label: 'project' },
                ]"
            />
            <div v-if="form.scope_type !== 'platform'" class="field">
                <label class="field-label">Scope id</label>
                <input
                    v-model="form.scope_id"
                    class="text-input"
                    :placeholder="
                        form.scope_type === 'tenant'
                            ? (auth.activeTenantId ?? 'tnt-…')
                            : 'prj-…'
                    "
                />
                <span v-if="form.scope_type === 'tenant'" class="field-hint">
                    Defaults to the active tenant when left empty.
                </span>
            </div>
            <template #footer>
                <button
                    class="btn btn-secondary"
                    type="button"
                    @click="createOpen = false"
                >
                    Cancel
                </button>
                <button
                    class="btn btn-primary"
                    type="button"
                    @click="createBinding"
                >
                    Create binding
                </button>
            </template>
        </ModalDialog>
    </div>
</template>

<style scoped>
.header-actions,
.row-actions {
    display: flex;
    gap: var(--space-xs);
}
.perm-row {
    display: flex;
    flex-direction: column;
    padding: 4px 0;
    border-bottom: 1px solid var(--color-hairline-soft);
}
.perm-key {
    font-size: 12.5px;
}
</style>
