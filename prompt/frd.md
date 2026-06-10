# Functional Requirements Document (FRD)

## Humanoid Robotics Physical AI Data & Compute Infrastructure Platform

**Version:** 1.0  
**Date:** 2026-06-10  
**Document type:** Functional Requirements Document  
**Output focus:** Business concepts, business processes, and functional requirements. This document intentionally avoids interface specifications, deployment architecture, protocol choices, latency targets, hardware topology, and other implementation-level constraints.

---

## 1. Executive Summary

The platform shall provide a converged data and compute infrastructure foundation for humanoid robotics Physical AI development. Its primary business purpose is to convert raw physical robot-operation recordings into governed, searchable, model-learnable data assets; expand and evaluate those assets through simulation and synthetic data workflows; train, evaluate, package, and govern Physical AI model candidates; and orchestrate the compute workflows needed to execute the full data-to-model loop.

The original concept contained the right strategic direction: a four-subsystem platform built around a data-and-model closed loop. This FRD keeps that converged structure but reduces overreach. It removes duplicate closed-loop features, relocates the 4D studio from “compute infrastructure” into a cross-cutting workbench capability, weakens unrealistic absolutes such as “microsecond-level alignment” and “absolute reliability,” and limits generative simulation features to governed scenario expansion and validated synthetic data generation.

The resulting platform is not a robot control system, not a safety-certified runtime, not an OTA delivery mechanism, not a custom physics engine, and not a general-purpose cloud platform. It is a Physical AI data, model, evaluation, orchestration, and compute operations platform for robotics engineering teams.

---

## 2. Research-Grounded Refinement Principles

The refinement is based on only high-consensus industry patterns observed across authoritative robotics, AI infrastructure, MLOps, simulation, data governance, and AI risk-management sources.

### 2.1 Applied consensus facts

| Area | Consensus applied in this FRD | Representative sources |
|---|---|---|
| Robotics data recording | Robot development commonly requires recording, replaying, sharing, and reproducing multi-topic robot data. | ROS 2 `ros2 bag` documentation; RLDS documentation |
| Sequential robot-learning data | Robot-learning datasets are commonly represented as episodes or trajectories with observations, actions, and task context. | Google Research RLDS; Open X-Embodiment |
| Cross-embodiment data standardization | Broad robot-learning work benefits from consistent dataset formats, metadata, and downstream training readiness. | Open X-Embodiment / RT-X; Google DeepMind blog |
| Simulation and synthetic data | Robot simulation and synthetic data workflows are useful for policy training, scenario variation, perception data generation, and evaluation, but generated data must be tracked and validated. | NVIDIA Isaac Sim, Isaac Lab, Replicator, Cosmos, Isaac Lab-Arena |
| Annotation workflows | Auto-labeling should be treated as pre-annotation or assisted labeling, with review and QA where quality matters. | AWS SageMaker Ground Truth; Label Studio; NVIDIA TAO Data Services |
| MLOps lineage | Experiments, model versions, model artifacts, datasets, parameters, metrics, and lineage should be tracked for reproducibility and governance. | MLflow Tracking and Model Registry; OpenLineage |
| AI risk governance | AI lifecycle governance should include risk mapping, measurement, management, accountability, documentation, and review. | NIST AI RMF |
| Workflow orchestration | Complex data and ML workflows are commonly represented as task graphs with dependencies, run history, retries, and operational monitoring. | Apache Airflow; Kubeflow Pipelines |
| Multi-tenant compute operations | Shared compute environments need quota, prioritization, resource visibility, and tenant-level governance. | Kubernetes multi-tenancy and resource quota documentation |

### 2.2 Important refinements from the original concept

1. **Preserve four subsystems, but reduce overlap.** The final architecture remains four-part: Data Factory, Simulation & Synthetic Data, ModelOps & Evaluation, and Orchestration & Compute Operations.
2. **Move “4D Studio” out of compute infrastructure.** It is a cross-cutting workbench used by data, annotation, simulation, evaluation, and failure analysis workflows.
3. **Do not promise universal microsecond alignment.** The platform shall preserve source timing and calibration metadata and align to task-specific tolerances defined by data owners.
4. **Do not promise absolute data reliability.** The platform shall provide measurable quality gates, review workflows, auditability, and acceptance thresholds.
5. **Treat VLM/VLA auto-annotation as assistive.** Foundation models may pre-label or suggest labels; human review, sampling, adjudication, and QA policies remain required for high-value datasets.
6. **Constrain generative synthesis.** NeRF, 3D Gaussian Splatting, world models, or other generative methods are not treated as open-ended core scope. They are permitted only as governed synthetic data or scene-reconstruction sources with provenance, validation, and usage limits.
7. **Separate data/model infrastructure from robot runtime.** OTA firmware delivery, robot control, real-time safety enforcement, and hardware-specific deployment operations are out of scope; artifact governance and release evidence are in scope.

---

## 3. Platform Purpose and Business Objectives

### 3.1 Purpose

The platform shall support the full engineering loop for humanoid robotics Physical AI:

**Capture physical robot data → curate and govern data assets → generate or vary training/evaluation scenarios → train and evaluate models → package release candidates → analyze failures → feed new data requirements back into data collection and simulation.**

### 3.2 Business objectives

| ID | Objective |
|---|---|
| BO-01 | Reduce the time and operational friction required to transform raw robot operation logs into model-ready datasets. |
| BO-02 | Improve dataset trust by making lineage, quality, annotation status, privacy classification, and usage restrictions visible and enforceable. |
| BO-03 | Increase coverage of rare, costly, or hazardous scenarios through governed simulation and synthetic data workflows. |
| BO-04 | Improve reproducibility of training and evaluation through versioned datasets, experiment tracking, model lineage, and immutable evaluation reports. |
| BO-05 | Create a unified failure-analysis loop that turns field failures, simulation failures, and evaluation failures into new data, simulation, and training work items. |
| BO-06 | Improve compute utilization and team coordination through workflow orchestration, quota management, job monitoring, and shared operational visibility. |
| BO-07 | Support release governance by linking every model candidate to its datasets, training runs, evaluation evidence, known limitations, and deployment package status. |

### 3.3 Success outcomes

The platform is successful when a robotics team can:

1. Register a data collection campaign and ingest raw robot recordings.
2. Validate, segment, annotate, review, and publish dataset snapshots.
3. Discover relevant real and synthetic scenarios for a target model capability.
4. Generate validated simulation or synthetic data tied to explicit coverage gaps.
5. Launch training and evaluation workflows with full lineage to data, code, parameters, and artifacts.
6. Compare model candidates using task-level, scenario-level, and safety-relevant evaluation evidence.
7. Package release candidates with auditable approval status and known limitations.
8. Trace model failures back to data gaps and launch targeted collection, annotation, simulation, or retraining workflows.

---

## 4. Scope

### 4.1 In scope

The platform shall include the following functional scope:

1. **Physical data ingestion and assetization** for multi-modal humanoid robotics recordings.
2. **Data quality, alignment, segmentation, annotation, and QA** workflows.
3. **Data catalog, search, mining, lineage, privacy classification, and dataset snapshot governance.**
4. **Simulation scenario management** linked to real robot data, failure cases, and evaluation requirements.
5. **Synthetic data generation and augmentation workflows** with provenance, validation, and usage controls.
6. **Model training experiment management** for robotics perception-action models, including VLA-oriented workflows where applicable.
7. **Physical AI model evaluation** across offline datasets, simulation scenarios, and approved real-world trial evidence records.
8. **Model registry, artifact governance, release candidate management, and approval evidence.**
9. **Workflow orchestration** across data, annotation, simulation, training, evaluation, and packaging jobs.
10. **Shared compute operations** including job prioritization, quota, utilization, monitoring, and tenant/project visibility.
11. **Cross-cutting 4D workbench** for synchronized review of video, point clouds, robot state, actions, annotations, predictions, and evaluation outcomes.

### 4.2 Out of scope

The following are explicitly out of scope for this FRD:

1. Real-time robot control loops.
2. Robot firmware development.
3. OTA transmission, robot fleet update execution, or remote robot actuation.
4. Safety-certified runtime enforcement.
5. Hardware board bring-up, silicon-specific kernel integration, or driver development.
6. Custom development of a physics engine or rendering engine.
7. General-purpose enterprise data lake unrelated to Physical AI.
8. General-purpose LLM training platform unrelated to robotics data and robotics model workflows.
9. Full teleoperation product functionality, except where teleoperation logs are ingested as source data.
10. Commercial labeling marketplace management.
11. Formal regulatory certification; the platform may provide evidence and audit records for external certification processes.

---

## 5. Definitions

| Term | Definition |
|---|---|
| Physical AI | AI systems that perceive, reason about, and act in the physical world through robots, embodied agents, or autonomous machines. |
| Humanoid robotics data | Multi-modal records generated by humanoid robot operation, including perception streams, proprioception, commands, actions, environment context, and task outcomes. |
| Raw recording | Original captured robot operation data before transformation, segmentation, labeling, or normalization. |
| Episode / trajectory | A bounded sequence of observations, actions, robot states, task context, and outcomes used for sequential decision learning, imitation learning, evaluation, or analysis. |
| Scenario | A business-level description of a task, environment, actors, objects, starting conditions, constraints, and expected outcome. |
| Data asset | A governed unit of data such as a raw recording, episode, annotation set, dataset snapshot, synthetic data batch, or evaluation dataset. |
| Dataset snapshot | An immutable, versioned dataset release with documented contents, lineage, quality status, usage restrictions, and owner approval. |
| Synthetic data | Generated or simulated data not directly captured from the physical robot or environment. Synthetic data must be clearly marked and governed separately from real data. |
| Pre-annotation | Machine-generated labels or suggestions that require review or acceptance according to the dataset QA policy. |
| Model candidate | A trained model version under evaluation or review. |
| Release candidate | A model candidate plus required metadata, evaluation evidence, artifact package, compatibility declaration, and approval status. |
| Evaluation suite | A governed collection of datasets, simulation scenarios, metrics, and acceptance criteria used to compare model candidates. |
| Closed loop | The business process by which failures, coverage gaps, and evaluation outcomes create targeted data, simulation, annotation, or retraining work. |

---

## 6. Refined Functional Architecture

### 6.1 Architecture summary

The platform shall be organized into four logical subsystems and one cross-cutting workbench capability.

| Subsystem | Name | Primary responsibility |
|---|---|---|
| A | Physical Data Factory & Asset Governance | Ingest, validate, align, segment, annotate, govern, search, mine, and publish real robot data assets. |
| B | Simulation & Synthetic Data Factory | Manage simulation scenarios and generate validated synthetic or augmented data tied to coverage gaps and evaluation needs. |
| C | Physical AI ModelOps & Evaluation | Plan, train, track, evaluate, register, document, and approve robotics model candidates and release candidates. |
| D | Workflow Orchestration & Compute Operations | Coordinate end-to-end task workflows, work requests, quotas, scheduling, monitoring, utilization, and tenant operations. |
| X | Integrated Physical AI Workbench | Provide synchronized 4D review and analysis across data, annotation, simulation, model prediction, action, and evaluation evidence. |

### 6.2 Architectural boundaries

1. The **Data Factory** owns data assets and dataset readiness.
2. The **Simulation Factory** owns synthetic/scenario assets and simulation-derived data readiness.
3. **ModelOps & Evaluation** owns model candidates, evaluation evidence, release candidate governance, and model lifecycle status.
4. **Orchestration & Compute Operations** owns workflow execution coordination, queue visibility, quota, utilization, and operational run history.
5. The **Workbench** is not a separate business subsystem; it is the common user experience used to inspect and validate records, labels, scenarios, model behavior, and failures.

---

## 7. Users and Responsibilities

| User role | Primary responsibilities |
|---|---|
| Data Collection Lead | Defines collection campaigns, task goals, robot/environment context, and expected data coverage. |
| Robotics Data Engineer | Ingests data, validates recordings, manages alignment, publishes dataset snapshots, and maintains lineage. |
| Annotator | Reviews and corrects labels, action segments, object annotations, captions, and task outcome records. |
| Annotation QA Lead | Defines labeling rubrics, review policy, sampling policy, adjudication rules, and dataset acceptance thresholds. |
| Simulation Engineer | Creates and governs simulation scenarios, scenario variants, synthetic batches, and validation status. |
| Model Engineer | Launches training jobs, compares experiments, manages model candidates, and prepares release candidates. |
| Evaluation Lead | Defines evaluation suites, acceptance criteria, model comparison reports, and failure triage. |
| Platform Operator | Manages workflows, quotas, job health, tenant operations, utilization, and operational incidents. |
| Governance / Release Approver | Reviews data restrictions, model evidence, known limitations, approval status, and release readiness. |
| Product / Program Manager | Tracks capability coverage, release milestones, risk status, cost, and throughput. |

---

## 8. Core Business Processes

### 8.1 Process BP-01: Real Robot Data to Governed Dataset Snapshot

1. Data Collection Lead creates a collection campaign with robot, environment, task, operator, consent/privacy, and coverage goals.
2. Raw recordings are ingested as immutable source assets.
3. The platform performs intake validation and produces a data quality report.
4. Data is aligned and normalized to a canonical episode/trajectory structure.
5. Long recordings are segmented into episodes, events, phases, and candidate atomic actions where relevant.
6. Machine-assisted pre-annotation may generate suggested labels, captions, object regions, or action segments.
7. Annotators review, correct, and submit labels.
8. QA reviewers sample, adjudicate, measure agreement or consistency, and approve or reject annotation sets.
9. Data engineers create dataset snapshots with quality status, lineage, usage restrictions, real/synthetic composition, and ownership.
10. Approved dataset snapshots become selectable for training, evaluation, mining, and scenario generation.

### 8.2 Process BP-02: Coverage Gap to Simulation or Synthetic Dataset

1. Evaluation Lead or Model Engineer identifies a failure cluster, rare condition, or coverage gap.
2. Simulation Engineer creates or selects scenarios linked to that gap.
3. Scenario variants are defined with business-level variation goals such as lighting, object position, task configuration, sensor condition, or environmental disturbance.
4. Simulation or synthetic data generation workflow is submitted.
5. Outputs are marked as synthetic and linked to source scenario, configuration, generator, validation report, and intended use.
6. Synthetic data is reviewed against quality and fitness criteria.
7. Approved synthetic assets are published as synthetic dataset snapshots or merged into mixed datasets only with explicit composition and weighting metadata.
8. Synthetic failures or artifacts create new correction, validation, or data collection tasks.

### 8.3 Process BP-03: Dataset Snapshot to Model Candidate

1. Model Engineer creates a training plan with target capability, robot embodiment, task scope, dataset snapshots, training objective, and evaluation suite.
2. Required approvals are obtained for restricted datasets or high-cost compute requests.
3. Training workflow is launched and tracked.
4. Training run captures dataset versions, run metadata, model artifacts, parameters, metrics, and owner.
5. Model candidate is registered with lineage, intended use, limitations, and evaluation readiness status.
6. Model candidate is submitted for evaluation.

### 8.4 Process BP-04: Model Candidate Evaluation to Release Decision

1. Evaluation Lead selects or creates an evaluation plan.
2. The platform executes offline dataset evaluation and simulation-based evaluation as applicable.
3. Approved real-world trial evidence may be ingested as evaluation evidence, but real robot execution is not controlled by the platform.
4. Evaluation report compares candidates against baseline and acceptance criteria.
5. Failures are clustered by task, environment, object, action phase, robot state, model output, and data coverage attributes where available.
6. Release candidate package is assembled with model artifact, evaluation evidence, dataset lineage, known limitations, deployment target class, and approval status.
7. Governance/Release Approver approves, rejects, or requests remediation.
8. Rejected or conditional candidates create data, simulation, annotation, or retraining work items.

### 8.5 Process BP-05: Closed-Loop Failure Management

1. Failure events originate from evaluation, simulation, real-world trial evidence, annotation QA, or post-deployment logs.
2. Failure events are triaged into categories such as perception, temporal reasoning, action prediction, manipulation, locomotion, safety-relevant behavior, data quality, or simulation artifact.
3. Each failure category is linked to candidate root causes and recommended next action.
4. Work items are opened for data mining, new collection, annotation correction, simulation scenario expansion, evaluation update, or model retraining.
5. Work item outcomes are tracked until the next model candidate is evaluated against the relevant failure cases.

### 8.6 Process BP-06: Workflow and Compute Operations

1. User submits a work request or launches a workflow template.
2. Platform checks project, access, quota, priority, cost center, and data restrictions.
3. Workflow is scheduled and executed as a set of dependent tasks.
4. Users and operators monitor progress, failures, retries, resource consumption, and results.
5. Completed workflow outputs are registered as data assets, simulation assets, training runs, model artifacts, evaluation reports, or release packages.
6. Operational history is retained for audit, cost review, and process improvement.

---

## 9. Functional Requirements

### Priority definitions

| Priority | Meaning |
|---|---|
| P0 | Required for the platform to deliver its core data-to-model closed loop. |
| P1 | Important for production maturity, governance, scale, or workflow efficiency. |
| P2 | Useful but intentionally constrained; should not be implemented until P0/P1 workflows are stable. |

---

## 9A. Subsystem A — Physical Data Factory & Asset Governance

### A1. Data collection campaign management

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-A1.1 | P0 | The platform shall allow authorized users to register a data collection campaign before or after data capture. | Each raw recording can be tied to an explicit business purpose, owner, robot context, and task scope. |
| FR-A1.2 | P0 | A campaign record shall capture the intended task, robot or embodiment, sensor modalities, environment, operator role, collection date range, and responsible team. | Data consumers can understand why the data exists and whether it is appropriate for a model or evaluation use case. |
| FR-A1.3 | P0 | A campaign record shall capture privacy, consent, safety-relevance, licensing, and usage restriction tags where applicable. | Restricted data is governed before it is used in datasets or model training. |
| FR-A1.4 | P1 | The platform shall allow teams to define target coverage goals for a campaign, such as task types, environments, objects, operator instructions, or failure modes. | Data collection can be measured against planned coverage rather than raw volume alone. |
| FR-A1.5 | P1 | The platform shall maintain campaign status values such as planned, collecting, ingesting, validating, published, suspended, and archived. | Program teams can track collection progress and blocked campaigns. |

### A2. Raw data ingestion and preservation

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-A2.1 | P0 | The platform shall ingest raw humanoid robot recordings as source assets without requiring destructive conversion. | Original evidence remains available for audit, reprocessing, and debugging. |
| FR-A2.2 | P0 | The platform shall support business ingestion modes for batch import and active collection/streamed capture. | Teams can onboard both historical recordings and current collection streams without creating separate business processes. |
| FR-A2.3 | P0 | The platform shall register common robotics modalities, including video, depth, point cloud or LiDAR, IMU, tactile/force, joint state, motor command, action token, language instruction, robot status, and environment context. | Multi-modal data can be cataloged consistently across robotics teams. |
| FR-A2.4 | P0 | The platform shall preserve source timestamps, source identifiers, robot identifiers, sensor identifiers, and capture-session metadata. | Downstream alignment, lineage, and reproducibility can be traced back to source data. |
| FR-A2.5 | P0 | The platform shall create an immutable raw asset record for each accepted recording. | No derived dataset can overwrite or obscure the original recording. |
| FR-A2.6 | P1 | The platform shall support ingest manifests that describe expected files, streams, modalities, and campaign associations. | Missing or unexpected data can be detected early. |
| FR-A2.7 | P1 | The platform shall allow users to quarantine recordings that are incomplete, restricted, corrupted, or awaiting review. | Suspect data is prevented from being accidentally used in model training or release evaluation. |

### A3. Intake validation and data quality

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-A3.1 | P0 | The platform shall create an intake validation report for each raw recording or batch. | Users can see whether data is ready for alignment, annotation, and dataset creation. |
| FR-A3.2 | P0 | The validation report shall identify missing modalities, unreadable files, duplicate assets, incomplete metadata, and obvious timestamp gaps. | Data quality issues are visible before expensive downstream processing. |
| FR-A3.3 | P0 | The platform shall classify data quality status using controlled states such as accepted, accepted with warnings, quarantined, rejected, or requires manual review. | Downstream workflows can enforce data readiness gates. |
| FR-A3.4 | P1 | The platform shall allow teams to define quality rules by campaign, robot embodiment, sensor suite, or dataset purpose. | Quality expectations can vary by task without hard-coding a universal rule. |
| FR-A3.5 | P1 | The platform shall record quality findings as searchable metadata. | Engineers can mine for recurring collection, calibration, sensor, or operator issues. |
| FR-A3.6 | P1 | The platform shall support remediation tasks for missing metadata, corruption review, privacy review, and recollection requests. | Data problems become trackable work rather than informal communication. |

### A4. Spatio-temporal alignment and canonical episode structure

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-A4.1 | P0 | The platform shall preserve source timing information and alignment assumptions for all derived records. | Users can audit how observations, states, and actions were aligned. |
| FR-A4.2 | P0 | The platform shall align multi-modal streams according to task-specific tolerance policies defined by authorized users. | Alignment is practical and auditable without making unrealistic universal precision claims. |
| FR-A4.3 | P0 | The platform shall flag records that cannot be aligned within the applicable tolerance policy. | Misaligned data does not silently enter model training or evaluation. |
| FR-A4.4 | P0 | The platform shall preserve or reference spatial calibration and coordinate-frame metadata needed to interpret sensor and robot-state relationships. | 3D/4D review, annotation, and model evaluation can use consistent spatial context. |
| FR-A4.5 | P0 | The platform shall normalize accepted recordings into a canonical episode or trajectory representation suitable for sequential robot-learning workflows. | Training and evaluation teams can consume data through a consistent business object. |
| FR-A4.6 | P1 | The canonical episode shall support observations, robot state, actions or commands, language/task instructions, environment context, annotations, and outcome labels where available. | Episodes can represent imitation learning, offline evaluation, and VLA-style training data without separate data products. |
| FR-A4.7 | P1 | The platform shall retain raw-to-derived lineage for every aligned episode. | Model and dataset lineage can trace back to original recordings and transformations. |

### A5. Event segmentation and scenario tagging

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-A5.1 | P0 | The platform shall allow long recordings to be segmented into episodes, events, phases, and task attempts. | Raw logs become usable units for training, annotation, evaluation, and failure analysis. |
| FR-A5.2 | P0 | The platform shall support manual segmentation and assisted segmentation suggestions. | Engineers can accelerate segmentation without depending entirely on automatic methods. |
| FR-A5.3 | P0 | Segments shall maintain references to source recordings and time ranges. | Users can inspect the original context for any derived segment. |
| FR-A5.4 | P1 | The platform shall support scenario tags such as task, environment, object, actor, robot posture, instruction type, outcome, and failure type. | Users can search and compose datasets by business-relevant robotics conditions. |
| FR-A5.5 | P1 | The platform shall support hierarchical action labels, such as task, phase, and atomic action, without enforcing a single universal taxonomy. | Teams can represent detail where needed while avoiding premature taxonomy lock-in. |
| FR-A5.6 | P1 | The platform shall allow scenario tags to be revised and versioned. | Teams can improve data semantics without losing historical reproducibility. |

### A6. Annotation, pre-annotation, and QA

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-A6.1 | P0 | The platform shall support annotation tasks for object labels, spatial regions, temporal events, action labels, task outcomes, language captions, and failure categories. | Core Physical AI labels can be produced under a single workflow. |
| FR-A6.2 | P0 | The platform shall treat foundation-model outputs as pre-annotations unless an authorized policy explicitly permits direct acceptance for a low-risk dataset. | Auto-labeling accelerates work without hiding uncertainty or bypassing review. |
| FR-A6.3 | P0 | Every pre-annotation shall record generator identity, generation time, confidence or quality signal where available, and review status. | Users can distinguish human-approved labels from machine suggestions. |
| FR-A6.4 | P0 | Annotators shall be able to accept, edit, reject, or comment on pre-annotations. | Human expertise remains part of high-quality dataset creation. |
| FR-A6.5 | P0 | Annotation projects shall define labeling instructions, allowed labels, review policy, and acceptance criteria. | Labeling is consistent and auditable across annotators and teams. |
| FR-A6.6 | P1 | The platform shall support QA sampling, overlap review, adjudication, and reviewer approval. | Dataset owners can measure and improve annotation quality. |
| FR-A6.7 | P1 | The platform shall maintain annotation versions and reviewer history. | Models can be traced to the exact labels used during training or evaluation. |
| FR-A6.8 | P1 | The platform shall allow high-value or ambiguous samples to be routed for expert review. | Scarce expert attention is focused where it is most valuable. |
| FR-A6.9 | P1 | The platform shall generate annotation throughput, rework, rejection, and quality reports by project. | Managers can see bottlenecks and quality risks in labeling operations. |

### A7. Data catalog, discovery, and mining

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-A7.1 | P0 | The platform shall provide a catalog of raw recordings, episodes, annotations, dataset snapshots, synthetic assets, and evaluation datasets. | Data assets are discoverable and governed as first-class business objects. |
| FR-A7.2 | P0 | Users shall be able to search by campaign, task, robot, environment, object, modality, annotation status, quality status, ownership, and dataset membership. | Engineers can find usable data without manual file hunting. |
| FR-A7.3 | P1 | Users shall be able to search or filter by scenario tags, failure categories, action labels, and evaluation outcomes. | The platform supports targeted edge-case mining and regression testing. |
| FR-A7.4 | P1 | Users shall be able to create reusable data cohorts from search results. | Teams can turn mining results into annotation, dataset, simulation, or evaluation work. |
| FR-A7.5 | P1 | The platform shall identify data assets that are overused, underused, deprecated, restricted, or superseded. | Dataset composition and governance risks are visible. |
| FR-A7.6 | P1 | The platform shall expose dataset coverage summaries by task, scenario, environment, robot, failure category, and real/synthetic composition. | Program leaders can steer data collection and simulation to coverage gaps. |

### A8. Dataset snapshots and data governance

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-A8.1 | P0 | The platform shall allow authorized users to publish immutable dataset snapshots. | Training and evaluation can be reproduced against fixed data releases. |
| FR-A8.2 | P0 | A dataset snapshot shall include asset membership, version, owner, purpose, quality status, annotation status, lineage, and publication time. | Dataset consumers can determine suitability and provenance. |
| FR-A8.3 | P0 | A dataset snapshot shall identify real, synthetic, augmented, and mixed data composition. | Synthetic data cannot be mistaken for real-world evidence. |
| FR-A8.4 | P0 | A dataset snapshot shall include usage restrictions, privacy tags, license tags, and retention status where applicable. | Restricted data is controlled during training and release processes. |
| FR-A8.5 | P0 | The platform shall prevent restricted or unapproved datasets from being selected for workflows that violate their usage policy. | Data governance is enforced at workflow selection time. |
| FR-A8.6 | P1 | The platform shall support dataset cards that summarize intended use, collection method, known gaps, quality limitations, and approval status. | Model and evaluation teams can understand dataset limitations. |
| FR-A8.7 | P1 | The platform shall support dataset deprecation and replacement links. | Teams can move away from obsolete datasets without losing lineage. |
| FR-A8.8 | P1 | The platform shall support audit history for dataset creation, approval, modification, deprecation, and access. | Governance reviews can reconstruct who did what and why. |

---

## 9B. Subsystem B — Simulation & Synthetic Data Factory

### B1. Scenario and digital asset catalog

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-B1.1 | P0 | The platform shall maintain a simulation scenario catalog linked to tasks, environments, objects, robot embodiments, and intended evaluation or training purpose. | Simulation assets are reusable and tied to business needs. |
| FR-B1.2 | P0 | Each scenario shall identify whether it is intended for training data generation, robustness testing, failure reproduction, evaluation, or demonstration. | Teams can distinguish scenario purpose before using outputs. |
| FR-B1.3 | P0 | Each scenario shall include owner, version, validation status, source inspiration, and known limitations. | Scenario use is governed rather than ad hoc. |
| FR-B1.4 | P1 | Scenarios shall be linkable to real-world episodes, failure events, or coverage gaps. | Real data and simulation reinforce each other in the closed loop. |
| FR-B1.5 | P1 | The platform shall support scenario collections for a robot capability, task family, or release evaluation plan. | Evaluation leads can build consistent benchmark suites. |

### B2. Simulation run management

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-B2.1 | P0 | The platform shall allow authorized users to submit simulation runs based on approved scenarios. | Simulation work is tracked and governed. |
| FR-B2.2 | P0 | A simulation run shall record scenario version, robot embodiment, task goal, variation plan, run owner, and intended output type. | Synthetic data and evaluation results can be traced to their generation context. |
| FR-B2.3 | P0 | The platform shall classify simulation run outputs as synthetic data, evaluation evidence, scenario diagnostics, or discarded outputs. | Downstream workflows can interpret outputs correctly. |
| FR-B2.4 | P1 | Simulation runs shall support comparison of model candidates in the same scenario collection. | Evaluation teams can compare behavior under controlled conditions. |
| FR-B2.5 | P1 | The platform shall capture simulation failure, artifact, and invalid-run reasons. | Simulation defects are separated from model failures. |
| FR-B2.6 | P1 | The platform shall support rerun requests from a prior simulation run record. | Teams can reproduce or refine scenario outcomes without rebuilding context manually. |

### B3. Synthetic data generation and augmentation

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-B3.1 | P0 | The platform shall generate synthetic or augmented data only from an approved scenario, approved generation request, or approved source dataset. | Synthetic data is controlled by a business purpose and provenance. |
| FR-B3.2 | P0 | Synthetic generation requests shall state the target coverage gap or evaluation objective. | Generated data volume is tied to need, not uncontrolled expansion. |
| FR-B3.3 | P0 | Synthetic outputs shall be marked as synthetic and linked to generator, source scenario, source data, generation settings, and validation status. | Synthetic lineage remains visible throughout training and evaluation. |
| FR-B3.4 | P1 | The platform shall support scenario variation categories such as lighting, object placement, scene layout, sensor condition, actor motion, physical disturbance, and task initial state. | Data diversity can be expanded using understandable robotics dimensions. |
| FR-B3.5 | P1 | The platform shall support generated labels or ground-truth annotations when available from the simulation or generator. | Synthetic data can be evaluated for training readiness. |
| FR-B3.6 | P2 | The platform may accept outputs from generative scene reconstruction or world-model tools only as governed candidate synthetic assets. | Advanced generation methods remain constrained, auditable, and non-default. |

### B4. Synthetic data validation and use controls

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-B4.1 | P0 | Synthetic datasets shall require validation status before selection for approved training or release evaluation workflows. | Unvalidated synthetic data does not silently influence model decisions. |
| FR-B4.2 | P0 | Validation reports shall state intended use, known limitations, failure modes, and whether the data is suitable for training, evaluation, or exploration only. | Synthetic data use is transparent and bounded. |
| FR-B4.3 | P1 | The platform shall allow dataset owners to define allowed synthetic-to-real composition policies for mixed datasets. | Teams can manage reliance on synthetic data. |
| FR-B4.4 | P1 | The platform shall track whether synthetic data improves, degrades, or has unknown effect on target evaluation results. | Synthetic data generation is judged by impact, not volume. |
| FR-B4.5 | P1 | The platform shall support deprecation of synthetic batches that are later found to be unrealistic, biased, or harmful to model performance. | Bad synthetic data can be removed from future training while preserving historical lineage. |

### B5. Real-to-sim and sim-to-real feedback loop

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-B5.1 | P0 | Real-world failures and evaluation failures shall be convertible into simulation scenario requests. | The platform turns failures into targeted scenario expansion. |
| FR-B5.2 | P1 | Simulation outcomes shall be linkable back to the original real-world failure, dataset gap, or evaluation requirement that motivated them. | Closed-loop traceability is preserved. |
| FR-B5.3 | P1 | Simulation failures that indicate missing real-world coverage shall be convertible into data collection or mining tasks. | Simulation informs real data acquisition rather than operating in isolation. |
| FR-B5.4 | P1 | The platform shall report scenario coverage by task, environment, object, failure category, and model release plan. | Program teams can assess whether evaluation coverage is growing in useful directions. |

---

## 9C. Subsystem C — Physical AI ModelOps & Evaluation

### C1. Training plan and experiment request management

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-C1.1 | P0 | The platform shall allow authorized users to create a training plan for a target robot capability, model family, embodiment, task scope, and evaluation objective. | Training work begins with explicit intent and evaluation criteria. |
| FR-C1.2 | P0 | A training plan shall bind to approved dataset snapshots rather than mutable data folders. | Training lineage is reproducible. |
| FR-C1.3 | P0 | The platform shall validate dataset usage restrictions before a training workflow can start. | Restricted data is not accidentally used. |
| FR-C1.4 | P1 | A training plan shall identify whether real, synthetic, augmented, or mixed datasets are used. | Data composition is visible during model comparison. |
| FR-C1.5 | P1 | Training plans shall support owner, project, cost center, priority, and approval status. | High-cost or sensitive model work can be governed. |
| FR-C1.6 | P1 | Training plans shall link to evaluation suites expected to judge the resulting model candidate. | Model development is aligned with acceptance criteria before compute is spent. |

### C2. Training run tracking

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-C2.1 | P0 | The platform shall track each training run as a governed record. | Training history can be searched, compared, and audited. |
| FR-C2.2 | P0 | A training run record shall include training plan, dataset snapshots, run owner, model family, run status, start/end time, and produced artifacts. | Users can reconstruct what created a model candidate. |
| FR-C2.3 | P0 | The platform shall capture training metrics and artifacts sufficient for model comparison and lineage. | Experiments are not evaluated only through informal notes. |
| FR-C2.4 | P0 | Failed or cancelled training runs shall record failure reason and reusable context where available. | Engineers can debug and rerun without losing context. |
| FR-C2.5 | P1 | Training runs shall support comparison across dataset versions, model candidates, and evaluation results. | Teams can understand what changed and why a candidate improved or regressed. |
| FR-C2.6 | P1 | The platform shall retain run lineage from dataset snapshots through model artifact and evaluation report. | Release reviews can trace each candidate end to end. |

### C3. Model registry and model documentation

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-C3.1 | P0 | The platform shall register each model candidate with a unique version and lifecycle status. | Model candidates are managed as governed assets. |
| FR-C3.2 | P0 | Model lifecycle status shall include states such as registered, evaluating, rejected, approved for limited trial, release candidate, released, deprecated, and archived. | Teams can distinguish experimental models from approved models. |
| FR-C3.3 | P0 | Model records shall include lineage to training run, dataset snapshots, code/build reference, evaluation reports, and artifact package. | Model provenance is visible for governance and reproducibility. |
| FR-C3.4 | P1 | Model records shall include a model card or equivalent summary of intended use, task scope, robot embodiment, known limitations, and evaluation coverage. | Release reviewers and downstream teams understand model boundaries. |
| FR-C3.5 | P1 | Model records shall support ownership, reviewers, approval history, and deprecation reason. | Accountability is visible through the model lifecycle. |
| FR-C3.6 | P1 | The platform shall allow baseline and challenger relationships between model versions. | Evaluation reports can show whether a candidate improves over accepted baselines. |
| FR-C3.7 | P1 | The platform shall prevent release-candidate creation unless required lineage and evaluation evidence are present. | Incomplete models do not enter release governance. |

### C4. Physical AI evaluation framework

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-C4.1 | P0 | The platform shall support evaluation suites that define datasets, scenarios, metrics, baselines, and acceptance criteria. | Model candidates are evaluated against repeatable expectations. |
| FR-C4.2 | P0 | Evaluation suites shall distinguish offline dataset evaluation, simulation evaluation, and real-world trial evidence records. | Evidence sources are not confused. |
| FR-C4.3 | P0 | Evaluation reports shall compare model candidates against baseline models and acceptance thresholds. | Release decisions are evidence-based. |
| FR-C4.4 | P0 | Evaluation metrics shall support task success, perception quality, temporal consistency, action prediction quality, collision or constraint violations, robustness across variations, and failure rate where applicable. | Physical AI behavior is assessed beyond generic loss or accuracy metrics. |
| FR-C4.5 | P1 | Evaluation reports shall break results down by task, environment, object class, robot state, action phase, failure category, and real/synthetic data source where applicable. | Engineers can identify exactly where a model performs poorly. |
| FR-C4.6 | P1 | The platform shall support manual review of evaluation episodes in the integrated workbench. | Evaluation failures can be inspected in physical context. |
| FR-C4.7 | P1 | Evaluation failures shall be convertible into data mining, annotation correction, simulation expansion, or retraining tasks. | Evaluation directly drives closed-loop improvement. |
| FR-C4.8 | P1 | Evaluation reports shall be immutable once approved, with superseding reports created for updated evaluations. | Release evidence remains auditable. |
| FR-C4.9 | P1 | The platform shall track evaluation coverage gaps. | Teams can improve test coverage before approving broad deployment. |

### C5. Release candidate and deployment artifact governance

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-C5.1 | P0 | The platform shall allow authorized users to assemble a release candidate from an approved or conditionally approved model candidate. | Model release preparation is governed as a formal business process. |
| FR-C5.2 | P0 | A release candidate shall include model artifact reference, model card, dataset lineage, evaluation evidence, target robot or deployment class, compatibility notes, known limitations, and rollback reference where applicable. | Release reviewers have the evidence needed to approve or reject. |
| FR-C5.3 | P0 | The platform shall support approval, rejection, conditional approval, and remediation-required outcomes. | Release decisions are explicit and auditable. |
| FR-C5.4 | P0 | The platform shall not execute OTA delivery or robot fleet update operations. | Scope remains limited to artifact governance and release evidence. |
| FR-C5.5 | P1 | The platform shall record packaging and optimization steps as artifact metadata when models are prepared for target runtime classes. | Edge deployment readiness can be traced without specifying low-level implementation details. |
| FR-C5.6 | P1 | The platform shall require reevaluation or reviewer acknowledgement when a release candidate changes artifact, dataset lineage, target deployment class, or limitations. | Significant changes cannot bypass governance. |
| FR-C5.7 | P1 | Released models shall remain linked to post-release logs, incidents, and failure-analysis records. | Model lifecycle remains closed-loop after release. |

### C6. Failure analysis and model improvement loop

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-C6.1 | P0 | The platform shall maintain failure records from evaluation, simulation, annotation QA, real-world trial evidence, and post-release logs. | Failures are structured assets, not scattered notes. |
| FR-C6.2 | P0 | Failure records shall include source, affected model or dataset, task, environment, failure category, severity, owner, and status. | Teams can prioritize and route remediation. |
| FR-C6.3 | P1 | The platform shall cluster or group failures by shared attributes such as task, object, action phase, scenario, or model output. | Repeated failures can be addressed as systematic gaps. |
| FR-C6.4 | P1 | Failure records shall link to remediation work items and eventual verification evidence. | Closed-loop improvement can be audited. |
| FR-C6.5 | P1 | The platform shall support regression sets created from prior failures. | Previously fixed failures can be evaluated before model promotion. |

---

## 9D. Subsystem D — Workflow Orchestration & Compute Operations

### D1. Workflow templates and task orchestration

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-D1.1 | P0 | The platform shall provide workflow templates for ingestion, validation, alignment, annotation, dataset publishing, simulation, synthetic generation, training, evaluation, packaging, and reporting. | Common Physical AI processes are repeatable. |
| FR-D1.2 | P0 | Workflows shall represent task dependencies and expected outputs. | Users can understand how work moves through the pipeline. |
| FR-D1.3 | P0 | Users shall be able to start, pause, cancel, rerun, and review workflow runs according to their permissions. | Operational control is available without manual infrastructure access. |
| FR-D1.4 | P0 | Workflow runs shall produce registered output assets where applicable. | Completed jobs create governed platform records rather than loose files. |
| FR-D1.5 | P1 | Workflow templates shall support parameterized business inputs such as campaign, dataset snapshot, scenario collection, model candidate, evaluation suite, and priority. | Teams can reuse workflows across projects while preserving context. |
| FR-D1.6 | P1 | Workflow runs shall retain status, owner, timeline, inputs, outputs, failure reason, and retry history. | Process execution is auditable and debuggable. |
| FR-D1.7 | P1 | Workflow templates shall be versioned. | Changes to workflows do not break reproducibility of historical runs. |

### D2. Work requests, priority, and approvals

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-D2.1 | P0 | The platform shall support work requests for data processing, annotation, simulation, training, evaluation, and packaging. | Teams can coordinate work through platform records. |
| FR-D2.2 | P0 | Work requests shall include requester, project, objective, inputs, priority, expected output, and required approval status. | Operations and governance teams can triage work consistently. |
| FR-D2.3 | P0 | The platform shall enforce approval requirements for restricted data, high-cost compute, release-critical evaluation, and release packaging. | Sensitive or expensive workflows are governed before execution. |
| FR-D2.4 | P1 | The platform shall support queue visibility by project, workflow type, priority, and status. | Teams can understand bottlenecks and plan around them. |
| FR-D2.5 | P1 | The platform shall support service classes such as exploratory, standard, release-critical, and incident-response. | Business priority can guide scheduling without technical implementation details. |
| FR-D2.6 | P1 | The platform shall retain approval decisions and reviewer comments. | Governance history is auditable. |

### D3. Compute resource allocation and utilization

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-D3.1 | P0 | The platform shall allocate shared compute capacity to projects, teams, or workspaces according to quotas and priorities. | Shared resources are used fairly and predictably. |
| FR-D3.2 | P0 | Users shall see requested, queued, running, completed, failed, and cancelled work by project or workspace. | Teams have operational visibility into compute work. |
| FR-D3.3 | P0 | Platform operators shall see utilization summaries for major workload classes such as data processing, simulation, training, evaluation, and packaging. | Operators can manage capacity at the business level. |
| FR-D3.4 | P1 | The platform shall support quota warnings and approval escalation when a request exceeds a project’s allowed allocation. | Cost and capacity risk are controlled before execution. |
| FR-D3.5 | P1 | The platform shall support priority adjustment by authorized users. | Urgent release or incident work can be expedited. |
| FR-D3.6 | P1 | The platform shall attribute resource consumption to project, team, campaign, model, workflow, or cost center. | Cost and utilization can be reviewed and optimized. |

### D4. Job monitoring and operational management

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-D4.1 | P0 | The platform shall provide job status monitoring for all workflow runs. | Users can know whether work is progressing, blocked, failed, or complete. |
| FR-D4.2 | P0 | Failed jobs shall record failure stage, failure category, affected inputs, and recommended next action where known. | Failures can be triaged without manual investigation from scratch. |
| FR-D4.3 | P1 | The platform shall provide operational dashboards for workflow throughput, backlog, failures, utilization, and data/model asset production. | Operators and leaders can track platform health and productivity. |
| FR-D4.4 | P1 | The platform shall support alerts for workflow failures, quota breaches, data quality blocks, evaluation regressions, and release approval blockers. | Important issues are surfaced promptly. |
| FR-D4.5 | P1 | The platform shall allow operators to annotate incidents and link them to affected workflow runs or assets. | Operational incidents are connected to their business impact. |
| FR-D4.6 | P1 | The platform shall support operational reports by project, team, capability, campaign, and release plan. | Management can review process performance and investment. |

### D5. Tenancy, roles, access, and audit

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-D5.1 | P0 | The platform shall organize work by workspace, project, or tenant. | Teams can collaborate while preserving ownership and governance boundaries. |
| FR-D5.2 | P0 | The platform shall support role-based permissions for collection, ingestion, annotation, QA, simulation, training, evaluation, release approval, and operations. | Users can perform their responsibilities without excessive access. |
| FR-D5.3 | P0 | Access to restricted data, sensitive model artifacts, release candidates, and evaluation evidence shall be controlled by policy. | Privacy, IP, and release risks are reduced. |
| FR-D5.4 | P0 | The platform shall audit user actions involving data access, dataset publication, annotation approval, training launch, evaluation approval, model promotion, and release candidate decision. | Governance teams can reconstruct critical decisions. |
| FR-D5.5 | P1 | The platform shall support project-level ownership and stewardship for data, scenario, model, workflow, and release assets. | Every important asset has an accountable owner. |
| FR-D5.6 | P1 | The platform shall support access review reports for restricted datasets and release artifacts. | Sensitive access can be periodically reviewed. |
| FR-D5.7 | P1 | The platform shall support retention and archival status for datasets, models, evaluation reports, and workflow records. | Historical assets can be retained or retired according to policy. |

---

## 9X. Cross-Cutting Capability — Integrated Physical AI Workbench

The original concept placed the 4D spatio-temporal studio under compute infrastructure. This FRD refines it as a shared workbench because it is used across data QA, annotation, simulation validation, model evaluation, and failure analysis.

| ID | Priority | Functional requirement | Business outcome / acceptance |
|---|---:|---|---|
| FR-X1.1 | P0 | The workbench shall provide synchronized review of video, spatial data, robot state, action records, annotations, predictions, and evaluation outcomes along a common timeline where data exists. | Engineers can understand what happened in a physical episode without switching between disconnected tools. |
| FR-X1.2 | P0 | Users shall be able to open raw recordings, aligned episodes, annotation tasks, simulation outputs, evaluation failures, and model comparison cases in the workbench. | The workbench supports the full data-to-model loop. |
| FR-X1.3 | P0 | The workbench shall clearly display asset status, source type, quality status, annotation status, synthetic/real indicator, model version, and evaluation context where applicable. | Users do not confuse raw, derived, synthetic, evaluated, or approved assets. |
| FR-X1.4 | P1 | Users shall be able to create comments, issue links, failure tags, and review decisions from the workbench. | Visual analysis can directly create actionable work. |
| FR-X1.5 | P1 | The workbench shall support side-by-side comparison of model candidates on the same episode or scenario where evaluation outputs exist. | Evaluation teams can inspect behavioral differences. |
| FR-X1.6 | P1 | The workbench shall support reviewer workflows for annotation QA and evaluation failure triage. | Review decisions are recorded in context. |
| FR-X1.7 | P1 | The workbench shall allow users to save views or cohorts for later review, dataset creation, simulation requests, or regression sets. | Valuable analysis can be reused in downstream workflows. |
| FR-X1.8 | P1 | Workbench activity affecting asset status, review decisions, or failure records shall be auditable. | Visual analysis contributes to the governance record. |

---

## 10. Business Rules

| ID | Business rule |
|---|---|
| BR-01 | Raw recordings shall remain immutable after acceptance into the platform. |
| BR-02 | Derived assets shall preserve lineage to source recordings and transformations. |
| BR-03 | Synthetic data shall always be labeled as synthetic and shall never be represented as direct real-world evidence. |
| BR-04 | Dataset snapshots selected for training or release evaluation shall be immutable. |
| BR-05 | Restricted datasets shall not be selectable for workflows outside their usage policy. |
| BR-06 | Pre-annotations shall not be treated as human-approved labels unless an explicit acceptance policy permits it. |
| BR-07 | Release candidates shall require model lineage, dataset lineage, evaluation evidence, owner, intended use, known limitations, and approval status. |
| BR-08 | Evaluation reports used for release decisions shall be immutable after approval. |
| BR-09 | Model candidates shall not be promoted to release candidate status when required evaluation evidence is missing or failed. |
| BR-10 | Failures from evaluation, simulation, real-world trial evidence, or post-release logs shall be triageable into remediation work items. |
| BR-11 | Simulation outputs shall be invalidated or deprecated if later determined to be unrealistic, mislabeled, or harmful to model quality. |
| BR-12 | Compute-intensive or restricted workflows shall follow project quota and approval policies. |
| BR-13 | Users shall have only the permissions required for their role and project. |
| BR-14 | Audit history shall be retained for critical data, annotation, model, evaluation, release, and workflow decisions. |

---

## 11. Key Business Data Objects

| Object | Description | Minimum business metadata |
|---|---|---|
| Collection Campaign | Planned or executed data collection effort. | Owner, project, purpose, task, robot, environment, coverage goals, privacy tags, dates, status. |
| Raw Recording | Immutable source robot operation recording. | Source ID, campaign, modalities, timestamps, robot, sensor suite, quality status, restrictions, lineage root. |
| Episode / Trajectory | Aligned and bounded sequence derived from raw recordings. | Source recording, time range, task, scenario tags, action labels, outcome, quality status, lineage. |
| Annotation Project | Managed labeling effort. | Dataset or cohort, instructions, label schema, annotators, reviewers, QA policy, status. |
| Annotation Set | Versioned labels for assets. | Label version, source asset, annotator, reviewer, pre-annotation provenance, approval status. |
| Dataset Snapshot | Immutable dataset version. | Asset list, owner, purpose, real/synthetic composition, quality status, restrictions, dataset card, lineage. |
| Scenario | Simulation or evaluation scenario. | Task, environment, robot, objects, variation plan, owner, validation status, source failure or gap. |
| Simulation Run | Execution of scenario or scenario collection. | Scenario version, run purpose, model candidate if applicable, outputs, validation status, failure reason. |
| Synthetic Data Batch | Generated or augmented data output. | Generator, scenario, source data, synthetic flag, validation report, intended use, limitations. |
| Training Plan | Planned model training request. | Objective, model family, dataset snapshots, evaluation suite, owner, priority, approvals. |
| Training Run | Executed training job. | Plan, inputs, metrics, artifacts, status, failure reason, lineage. |
| Model Candidate | Registered trained model version. | Version, owner, lineage, intended use, limitations, evaluation status, lifecycle state. |
| Evaluation Suite | Governed model test collection. | Datasets, scenarios, metrics, baselines, thresholds, scope, owner. |
| Evaluation Report | Results of model evaluation. | Candidate, suite, metrics, breakdowns, failures, baseline comparison, approval status. |
| Release Candidate | Model candidate plus release evidence. | Artifact package, target deployment class, evaluation evidence, model card, approvals, limitations. |
| Failure Record | Structured model/data/simulation failure. | Source, severity, task, scenario, model, dataset, category, owner, status, remediation. |
| Workflow Run | Executed platform workflow. | Template, inputs, outputs, owner, project, status, timing, resource attribution, failure reason. |
| Work Request | User request for work execution. | Requester, objective, inputs, priority, approvals, status, linked workflow. |

---

## 12. Reporting and Dashboard Requirements

| ID | Priority | Report / dashboard requirement | Business purpose |
|---|---:|---|---|
| RPT-01 | P0 | Data ingestion status by campaign, project, modality, and quality status. | Track collection and onboarding progress. |
| RPT-02 | P0 | Dataset snapshot inventory with owner, purpose, composition, restrictions, and approval status. | Help teams select governed datasets. |
| RPT-03 | P1 | Dataset coverage by task, environment, object, robot, failure category, and real/synthetic mix. | Identify gaps for new collection or simulation. |
| RPT-04 | P1 | Annotation throughput, QA pass rate, rework rate, and unresolved review queue. | Manage labeling operations. |
| RPT-05 | P1 | Simulation scenario coverage and validation status. | Understand synthetic/evaluation readiness. |
| RPT-06 | P0 | Training run inventory and status by model family, project, owner, and dataset version. | Coordinate model development work. |
| RPT-07 | P0 | Model candidate comparison by evaluation suite, baseline, task, scenario, and failure category. | Support evidence-based model selection. |
| RPT-08 | P0 | Release candidate status with missing evidence, approval blockers, and known limitations. | Support release governance. |
| RPT-09 | P1 | Closed-loop failure dashboard from detection through remediation and verification. | Ensure failures lead to concrete improvement. |
| RPT-10 | P1 | Compute utilization, queue, quota, cost attribution, and workflow failure trends. | Manage shared compute operations. |
| RPT-11 | P1 | Access and audit report for restricted datasets, sensitive artifacts, and release decisions. | Support governance and compliance review. |

---

## 13. Acceptance Criteria

The following acceptance criteria define a coherent end-to-end platform release at FRD level.

| ID | Acceptance criterion |
|---|---|
| AC-01 | A user can register a collection campaign, ingest raw multi-modal robot recordings, and view intake validation results. |
| AC-02 | A user can create aligned episodes from accepted recordings and inspect them in the integrated workbench. |
| AC-03 | A user can create an annotation project, review pre-annotations, complete human labeling, perform QA review, and publish an approved annotation set. |
| AC-04 | A data owner can publish an immutable dataset snapshot with real/synthetic composition, lineage, quality status, restrictions, and dataset card. |
| AC-05 | A user can search for episodes by task, object, environment, quality status, annotation status, failure category, and dataset membership. |
| AC-06 | A simulation engineer can create a scenario linked to a real failure or coverage gap and launch a governed synthetic generation or evaluation run. |
| AC-07 | Synthetic data produced by the platform is clearly marked, validated, governed, and traceable to scenario and generation request. |
| AC-08 | A model engineer can create a training plan using approved dataset snapshots and launch a tracked training workflow. |
| AC-09 | A model candidate is registered with lineage to training run, dataset snapshots, artifacts, and evaluation status. |
| AC-10 | An evaluation lead can execute an evaluation suite and produce an immutable evaluation report comparing candidate and baseline performance. |
| AC-11 | Evaluation failures can be reviewed in the workbench and converted into remediation work items for data, annotation, simulation, or retraining. |
| AC-12 | A release candidate cannot be approved unless required lineage, evidence, owner, intended use, limitations, and approval records are present. |
| AC-13 | Operators can view workflow queue, job status, failures, utilization, quota, and project-level resource attribution. |
| AC-14 | Governance users can audit critical dataset, annotation, model, evaluation, release, and access decisions. |

---

## 14. Requirements Traceability Summary

| Business objective | Primary supporting requirements |
|---|---|
| BO-01 | FR-A2, FR-A3, FR-A4, FR-A5, FR-D1 |
| BO-02 | FR-A6, FR-A7, FR-A8, FR-D5, BR-01 to BR-06 |
| BO-03 | FR-B1, FR-B2, FR-B3, FR-B4, FR-B5 |
| BO-04 | FR-A8, FR-C1, FR-C2, FR-C3, FR-C4, FR-D1 |
| BO-05 | FR-B5, FR-C4, FR-C6, FR-X1 |
| BO-06 | FR-D1, FR-D2, FR-D3, FR-D4 |
| BO-07 | FR-C3, FR-C4, FR-C5, FR-D5, BR-07 to BR-10 |

---

## 15. Open Decisions and Controlled Assumptions

These items require product or business decision but do not block this FRD.

| ID | Item | Required decision |
|---|---|---|
| OD-01 | Canonical robot data schema | Decide which internal representation will be used for episodes and trajectories, and which external formats must be importable or exportable. |
| OD-02 | Alignment tolerance policies | Define tolerance policies by robot, sensor suite, modality, and task family. |
| OD-03 | Label taxonomy governance | Decide who owns the action/task/failure taxonomy and how changes are approved. |
| OD-04 | Synthetic data approval criteria | Define validation thresholds and allowed use cases for synthetic data. |
| OD-05 | Release approval policy | Define which model changes require governance approval, safety review, or external review. |
| OD-06 | Real-world trial evidence | Define how real-world trial results are produced outside the platform and ingested as evidence. |
| OD-07 | Tenant and quota model | Define whether quotas are assigned by team, project, model program, cost center, or release line. |
| OD-08 | Retention policies | Define retention for raw recordings, derived datasets, models, evaluation reports, logs, and audit history. |

---

## 16. Reference Sources

The following sources informed the restrained refinement of the concept. They are included for traceability, not to prescribe specific vendors or implementation choices.

1. Original uploaded concept: `idea(1).md`.
2. ROS 2 Documentation, “Recording and playing back data”: https://docs.ros.org/en/rolling/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html
3. ROS 2 message_filters documentation: https://docs.ros.org/en/rolling/p/message_filters/doc/Tutorials/Approximate-Synchronizer-Python.html
4. Google Research RLDS: https://github.com/google-research/rlds
5. Google Research Blog, “RLDS: An Ecosystem to Generate, Share, and Use Datasets in Reinforcement Learning”: https://research.google/blog/rlds-an-ecosystem-to-generate-share-and-use-datasets-in-reinforcement-learning/
6. Open X-Embodiment project: https://robotics-transformer-x.github.io/
7. Google DeepMind Blog, “Scaling up learning across many different robot types”: https://deepmind.google/blog/scaling-up-learning-across-many-different-robot-types/
8. NVIDIA Isaac Sim Documentation: https://docs.isaacsim.omniverse.nvidia.com/
9. NVIDIA Isaac Sim Replicator Documentation: https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/index.html
10. NVIDIA Isaac Lab: https://developer.nvidia.com/isaac/lab
11. NVIDIA Isaac Lab-Arena: https://developer.nvidia.com/isaac/lab-arena
12. NVIDIA Cosmos: https://www.nvidia.com/en-us/ai/cosmos/
13. AWS SageMaker Ground Truth documentation: https://docs.aws.amazon.com/sagemaker/latest/dg/data-label.html
14. Label Studio documentation: https://labelstud.io/guide/predictions
15. NVIDIA TAO Auto-Label service documentation: https://docs.nvidia.com/tao/tao-toolkit/latest/text/data_services/auto-label.html
16. MLflow Tracking documentation: https://mlflow.org/docs/latest/ml/tracking/
17. MLflow Model Registry documentation: https://mlflow.org/docs/latest/ml/model-registry/
18. OpenLineage: https://openlineage.io/
19. NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
20. Apache Airflow documentation: https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html
21. Kubeflow Pipelines documentation: https://www.kubeflow.org/docs/components/pipelines/overview/
22. Kubernetes Multi-Tenancy documentation: https://kubernetes.io/docs/concepts/security/multi-tenancy/
23. Kubernetes Resource Quotas documentation: https://kubernetes.io/docs/concepts/policy/resource-quotas/
24. ONNX: https://onnx.ai/
25. PyTorch ExecuTorch Documentation: https://docs.pytorch.org/executorch/stable/index.html
26. NVIDIA TensorRT Developer page: https://developer.nvidia.com/tensorrt

---

## 17. Appendix — Refined Module Plan

### Original module plan retained, corrected, and converged

| Refined module | Original source area | Key changes |
|---|---|---|
| Physical Data Factory & Asset Governance | Multi-Modal Physical Data Factory & Loop | Merged data lake, alignment, annotation, governance, and mining into one coherent data-asset lifecycle. Removed exaggerated precision and reliability claims. |
| Simulation & Synthetic Data Factory | Dual-Driven Twin Data Generation & Simulation | Kept simulation, domain variation, and synthetic generation but constrained them to validated scenario workflows with explicit provenance and use controls. |
| Physical AI ModelOps & Evaluation | Closed-Loop ModelOps / VLA ModelOps | Kept training, experiment lineage, evaluation, artifact governance, and release readiness. Removed OTA execution and runtime control from scope. |
| Workflow Orchestration & Compute Operations | Full-Pipeline Task Orchestration & Compute Infrastructure | Kept workflow orchestration, quota, scheduling, monitoring, and tenancy. Removed “ultimate performance guarantee” language and implementation-specific hard slicing assumptions. |
| Integrated Physical AI Workbench | Multi-Modal 4D Spatio-Temporal Studio | Reclassified as a cross-cutting review, annotation, evaluation, and failure-analysis capability rather than a compute infrastructure feature. |
