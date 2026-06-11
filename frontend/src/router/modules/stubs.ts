/**
 * Zero-implementation navigation entries for out-of-scope modules M04-M20
 * (scope lock): placeholder route + empty page shell only.
 */
import type { RouteRecordRaw } from 'vue-router'

export interface StubModuleDef {
  id: string
  name: string
  path: string
  group: string
  icon: string
}

export const STUB_MODULES: StubModuleDef[] = [
  { id: 'M04', name: 'Campaigns', path: '/data/campaigns', group: 'Data Factory', icon: 'flag' },
  { id: 'M05', name: 'Ingestion & Quality', path: '/data/ingestion', group: 'Data Factory', icon: 'upload' },
  { id: 'M06', name: 'Episodes & Segmentation', path: '/data/episodes', group: 'Data Factory', icon: 'film' },
  { id: 'M07', name: 'Annotation & QA', path: '/data/annotation', group: 'Data Factory', icon: 'tag' },
  { id: 'M08', name: 'Catalog & Snapshots', path: '/data/catalog', group: 'Data Factory', icon: 'database' },
  { id: 'M09', name: 'Scenarios', path: '/sim/scenarios', group: 'Simulation Factory', icon: 'map' },
  { id: 'M10', name: 'Simulation & Synthetic', path: '/sim/runs', group: 'Simulation Factory', icon: 'cpu' },
  { id: 'M11', name: 'Training', path: '/mlops/training', group: 'ModelOps', icon: 'activity' },
  { id: 'M12', name: 'Model Registry', path: '/mlops/models', group: 'ModelOps', icon: 'box' },
  { id: 'M13', name: 'Evaluation', path: '/mlops/evaluation', group: 'ModelOps', icon: 'check-circle' },
  { id: 'M14', name: 'Release Governance', path: '/mlops/releases', group: 'ModelOps', icon: 'shield' },
  { id: 'M15', name: 'Failure Analysis', path: '/mlops/failures', group: 'ModelOps', icon: 'alert' },
  { id: 'M16', name: 'Orchestration', path: '/orchestration/runs', group: 'Operations', icon: 'workflow' },
  { id: 'M17', name: 'Compute & Quota', path: '/ops/quotas', group: 'Operations', icon: 'gauge' },
  { id: 'M18', name: 'Analytics & Mining', path: '/analytics/search', group: 'Cross-Cutting', icon: 'search' },
  { id: 'M19', name: '4D Workbench', path: '/workbench', group: 'Cross-Cutting', icon: 'layers' },
  { id: 'M20', name: 'Notifications', path: '/notifications', group: 'Cross-Cutting', icon: 'bell' },
]

const routes: RouteRecordRaw[] = STUB_MODULES.map((m) => ({
  path: m.path,
  name: `stub-${m.id.toLowerCase()}`,
  component: () => import('@/views/stubs/StubPage.vue'),
  meta: { title: m.name, stubId: m.id, stubName: m.name },
}))

export default routes
