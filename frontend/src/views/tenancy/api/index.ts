/** M02 module API facade — re-exports only the generated services and types
 * this module consumes (ARCHITECTURE §4.1). */
export {
  m02ArchiveProject,
  m02CreateProject,
  m02CreateResourceBinding,
  m02CreateTenant,
  m02DecommissionResource,
  m02GetProject,
  m02GetResource,
  m02GetTenant,
  m02GetTenantSelf,
  m02ListProjectMembers,
  m02ListProjects,
  m02ListResourceBindings,
  m02ListResources,
  m02ListTenantBindingsSelf,
  m02ListTenants,
  m02ReactivateTenant,
  m02RegisterResource,
  m02ReleaseResourceBinding,
  m02RemoveProjectMember,
  m02SuspendTenant,
  m02UpdateProject,
  m02UpdateTenant,
  m02UpsertProjectMember,
} from '@/api/generated/sdk.gen'
export { m03ListUsers as m02LookupUsers } from '@/api/generated/sdk.gen'
export type {
  BindingOut,
  BindingPublicOut,
  MemberOut,
  ProjectOut,
  ResourceCreate,
  ResourceOut,
  TenantOut,
  TenantPublicOut,
} from '@/api/generated/types.gen'
