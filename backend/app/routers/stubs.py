"""Zero-implementation stubs for out-of-scope modules M04-M20.

Scope lock: every endpoint family of the FDD §1.5 contract index outside
M01/M02/M03 answers 501 E_NOT_IMPLEMENTED. No business logic, no schema, no
persistence. Routes are data-driven catch-alls per documented path prefix.
"""
from fastapi import APIRouter, Response

from app.core.errors import ERROR_REGISTRY
from app.schemas.response import ApiResponse, ErrorData

router = APIRouter(tags=["Stubs (M04-M20)"], include_in_schema=False)

# (module id, module name, top-level path segments owned by the module)
STUB_MODULES: list[tuple[str, str, list[str]]] = [
    ("M04", "Data Collection Campaign Management", ["campaigns"]),
    ("M05", "Data Ingestion & Quality Management",
     ["ingest-manifests", "ingest-sessions", "recordings", "quality-rules", "remediation-tasks"]),
    ("M06", "Alignment, Episode & Segmentation Management",
     ["alignment-policies", "alignment-jobs", "episodes", "segments", "segmentation-suggestions", "taxonomies"]),
    ("M07", "Annotation & QA Management",
     ["annotation-projects", "annotation-tasks", "preannotation-jobs", "preannotations",
      "qa-reviews", "annotation-sets", "qa-samples"]),
    ("M08", "Data Catalog & Dataset Snapshot Governance",
     ["catalog", "assets", "dataset-snapshots", "usage-policies"]),
    ("M09", "Scenario Management", ["scenarios", "scenario-collections", "scenario-requests"]),
    ("M10", "Simulation Run & Synthetic Data Management",
     ["simulation-runs", "generation-requests", "synthetic-batches", "composition-policies"]),
    ("M11", "Training Management", ["training-plans", "training-runs"]),
    ("M12", "Model Registry", ["model-candidates", "model-families"]),
    ("M13", "Evaluation Management",
     ["evaluation-suites", "evaluation-runs", "evaluation-reports", "trial-evidence",
      "regression-sets", "evaluation-coverage"]),
    ("M14", "Release Candidate Governance", ["release-candidates", "post-release-logs"]),
    ("M15", "Failure Analysis & Closed-Loop Management", ["failure-records", "failure-clusters", "failure-tags"]),
    ("M16", "Workflow Orchestration & Work Request Management",
     ["workflow-templates", "workflow-runs", "work-requests", "approvals", "queues"]),
    ("M17", "Compute Operations & Quota Management",
     ["quota-policies", "quota", "utilization", "consumption", "jobs", "incidents",
      "alert-rules", "ops-dashboard"]),
    ("M18", "Analytics & Mining",
     ["search", "embedding-spaces", "embedding-jobs", "distribution-jobs",
      "distribution-reports", "visualizations", "cohorts", "coverage-summaries", "coverage-gaps"]),
    ("M19", "Integrated 4D Workbench",
     ["workbench-sessions", "comparison-sessions", "comments", "saved-views"]),
    ("M20", "Notification & Alerting", ["notifications", "notification-preferences"]),
    # Reports family (per-module RPT endpoints) — all owned by stub modules.
    ("RPT", "Reports", ["reports"]),
]

_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

_HTTP_501, _CODE_501 = ERROR_REGISTRY["E_NOT_IMPLEMENTED"]


def _make_stub(module_id: str, module_name: str):
    async def stub(rest: str = "") -> Response:
        envelope = ApiResponse[ErrorData](
            code=_CODE_501,
            message=f"{module_id} {module_name} is not implemented in this release.",
            data=ErrorData(error_code="E_NOT_IMPLEMENTED", details=[{"module": module_id}]),
        )
        return Response(
            content=envelope.model_dump_json(), status_code=_HTTP_501, media_type="application/json"
        )

    return stub


for module_id, module_name, segments in STUB_MODULES:
    handler = _make_stub(module_id, module_name)
    for segment in segments:
        for prefix in (
            f"/api/v1/{segment}",
            f"/api/v1/projects/{{project_id}}/{segment}",
            f"/api/v1/tenants/{{tenant_id}}/{segment}",
            f"/api/v1/admin/{segment}",
            f"/api/v1/users/me/{segment}",
        ):
            router.add_api_route(
                prefix, handler, methods=_METHODS, operation_id=None, include_in_schema=False
            )
            router.add_api_route(
                prefix + "/{rest:path}",
                handler,
                methods=_METHODS,
                operation_id=None,
                include_in_schema=False,
            )
