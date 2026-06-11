/** M01 module API facade — re-exports only the generated services and types
 * this module consumes (ARCHITECTURE §4.1). */
export {
  m01AdminRevokeUserSessions,
  m01CreateSession,
  m01CurrentSession,
  m01Logout,
  m01RequestLoginCode,
  m01SwitchActiveTenant,
} from '@/api/generated/sdk.gen'
export type {
  CurrentSessionResponse,
  LoginCodeAccepted,
  SessionCreated,
  TenantMembershipInfo,
} from '@/api/generated/types.gen'
