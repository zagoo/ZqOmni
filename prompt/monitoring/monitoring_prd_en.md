# Product Design Document v1.0 for the Compute Resource Monitoring Module of a Large-Model Training Platform

> Role positioning: AI Infra platform product / SRE / training performance analysis / multi-cloud compute operations  
> Target form: Single-page SPA, multi-tab, multi-card, Notion-style monitoring workspace  
> Scope: Multi-Region, multi-cluster, multi-type AI accelerator cards, including NVIDIA H200, NVIDIA RTX PRO 5000 Blackwell, Alibaba Cloud Zhenwu PPU, and future extensible NPU/GPU/ASIC adapters  
> Design principle: Rich enough metrics, restrained homepage; clear flow from global view to drill-down; every metric can be explained, compared, filtered, aggregated, and traced

---

## 0. Overall description

1. **First establish a closed loop around product problems**: Users are not here to “look at a pile of metrics.” They need to answer: Is compute healthy? Are resources wasted? Why is training slower? Which Region, accelerator model, or job is dragging performance down? Do we need to migrate or scale out?
2. **Layer metrics instead of flattening them**: The five-layer metric taxonomy in `monitoring_metrics.md` is compressed into a three-level display strategy:
   - L0 homepage core metrics: for on-call engineers, managers, and resource operations to make fast judgments.
   - L1 standard analysis metrics: for daily troubleshooting by SREs and training engineers.
   - L2 expert diagnostic metrics: opened only for performance optimization, chip adaptation, and framework tuning.
3. **Multi-Region and multi-accelerator-type support is a capability of the underlying data model, not just a few filters**: A unified `accelerator` abstraction is introduced, with vendor adapters integrating DCGM/NVML, PPU SDK, Kubernetes, NCCL, profilers, eBPF, network exporters, and storage exporters.
4. **The UI is implemented at pixel-level detail using Notion’s design language**: The document provides page structure, dimensions, colors, typography, cards, tabs, tooltips, drawers, tables, trend charts, and responsive rules.
5. **Every interaction that triggers backend requests is bound to an API**: Including page load, tab switching, filtering, aggregation, TopN, trend refresh, drill-down, metric explanations, alert acknowledgement, saved views, export, and more.
6. **Design review conclusions are added**: The design is repeatedly reviewed from four perspectives: AI Infra SRE, GPU/NCCL performance expert, platform product expert, and frontend interaction expert, to avoid “metric greed” and “pretty but unusable UI.”

---

## 1. Product Positioning and Boundaries

### 1.1 One-Sentence Product Definition

A **cross-Region heterogeneous compute resource monitoring and analysis workspace** for large-model training platforms, enabling platform teams to complete compute health inspection, resource utilization analysis, training bottleneck diagnosis, single-accelerator anomaly drill-down, aggregate trend comparison, and alert closure in one page.

### 1.2 Core Users

| User Role | Typical Questions | Highest-Frequency Actions | Required Default View |
|---|---|---|---|
| Platform SRE / On-call engineer | Are there offline cards, overheating, Xid, ECC, or network anomalies right now? | Check global health, Top anomalies, acknowledge alerts, drill down to nodes | Overview + Alerts |
| Training engineer | Why is my job slower? Is it compute, communication, IO, or memory? | Search job, inspect step-time breakdown, inspect single-accelerator/Pod trends | Job Analysis |
| Resource operations / FinOps | Which cards are idle? Which teams have poor resource efficiency? | Aggregate by tenant, Region, and card model; find low-utilization TopN | Overview + Cost & Capacity |
| Platform administrator | Which Region or accelerator model needs scaling, retirement, or migration? | Compare cross-Region/model trends and capacity forecasts | Trends + Resources |
| Chip/framework adaptation engineer | Are metrics complete for the new accelerator model or PPU? Is performance as expected? | Inspect metric dictionary, driver/SDK versions, expert metrics | Resources + Settings |

### 1.3 What This Module Does Not Do

This module is not a complete APM, not a training experiment management platform, not a cost billing platform, and not a generic BI tool. It does one thing: **around training compute, it connects hardware health, resource utilization, training efficiency, and operational cost into a monitoring experience that is diagnosable, aggregatable, and drillable**.

---

## 2. Professional References and Domain Basis

### 2.1 How Uploaded Internal Documents Are Used

| Document | How It Is Used |
|---|---|
| `monitoring_metrics.md` | Primary source for the metric taxonomy. Its five-layer architecture is retained: hardware, system runtime, training framework, job/model, and business cost. Display priority is productized and trimmed by P0/P1/P2/P3. |
| `DESIGN.md` | Source for UI visual and component specifications. The design adopts Notion-style colors, typography, cards, tabs, buttons, spacing, border radius, and responsive rules. |

### 2.2 How External Professional Materials Are Used

| Source Type | How It Is Applied in the Product Design |
|---|---|
| NVIDIA DCGM / DCGM Exporter official documentation | Used for NVIDIA GPU telemetry collection. DCGM Exporter exposes metrics to Prometheus through `/metrics`; the metric dictionary retains mapping to DCGM field IDs. |
| Kubernetes Metrics Server / kubelet resource metrics official documentation | Used as one of the data sources for Pod / Node / Container CPU, memory, resource request, and scheduling-related metrics. |
| Prometheus official query functions | Used as the basis for range aggregation, avg/sum/count over time, TopN, rate/increase, histogram quantile, and similar query capabilities. |
| Thanos / Mimir / OpenTelemetry official documentation | Used as architectural references for unified multi-Region and multi-cluster metric querying, long-term storage, multi-tenancy, and a unified metrics data model. |
| NVIDIA H200 / RTX PRO 5000 official specifications | Used as accelerator capability metadata. Metric semantics are not hardcoded from specs, but specs are used for normalization such as peak compute, memory capacity, power limit, and bandwidth. |
| Alibaba Cloud Zhenwu PPU / PAI-PPU documentation | Used as the basis for PPU adaptation. At the product layer, a PPU is abstracted as an accelerator; NVIDIA-only concepts are not forced onto PPU. |
| NCCL / PyTorch Profiler official documentation | Used for distributed communication, step-level performance breakdown, operator latency, and profiler-based expert mode. |

### 2.3 Expert Review Perspectives

Real-time consultation with external human experts cannot be initiated here, so this design concretizes “expert review” into four review perspectives and provides review conclusions in core sections:

| Expert Perspective | Review Focus | Implementation in This Version |
|---|---|---|
| AI Infra SRE | Whether failures can be discovered quickly, whether metrics are alertable, and whether issues can be located to node/card/Pod/job | The homepage only exposes P0/P1 metrics; every anomalous accelerator, node, and job can drill down to an event timeline. |
| GPU/NCCL performance expert | Whether GPU utilization, SM/Tensor utilization, MFU, communication wait, and data wait are distinguished | The metric dictionary includes “differences from similar metrics”; the Job page breaks down compute, communication, IO, and waiting. |
| Platform product expert | Whether metric piling is avoided and whether troubleshooting follows a natural user path | The information architecture follows “Overview → aggregate comparison → TopN → single-card/job drill-down → alert/remediation.” |
| Frontend interaction expert | Whether the page is immediately understandable and whether filters/tooltips are convenient | Uses Notion-style lightweight cards, pill tabs, right-side drawer, metric explanation popovers, and saved views. |

---

## 3. Product Problem Closed Loop

### 3.1 Six Questions That Must Be Answered

| ID | User Question | First-Screen Answer | Drill-Down Answer |
|---|---|---|---|
| Q1 | Is overall compute healthy right now? | Healthy card ratio, anomalous card count, P0 alert count, unavailable card count | Anomalous card list, node events, Xid/ECC/offline/temperature timeline |
| Q2 | Are resources being used effectively? | Allocated cards, active training cards, average utilization, low-utilization card TopN | Low-utilization causes split by Region/model/tenant/job |
| Q3 | Which Region or accelerator model is dragging performance down? | Region × model matrix, utilization/failure rate/queue time | Enter Region or model details to inspect trends and TopN |
| Q4 | Why is a specific job slow? | Step time, Tokens/s, MFU, communication/data wait ratio | Single-card trends, communication operators, DataLoader, checkpoint, Pod events |
| Q5 | Is there resource waste or cost anomaly? | Idle card-hours, low-utilization card-hours, cost per million tokens | Tenant/user/job cost ranking and Goodput trend |
| Q6 | Do we need migration, scaling, or throttling? | Capacity watermark, queue depth, SLO attainment | Historical trend, forecast, resource fragmentation, scheduling failure reasons |

### 3.2 Main User Path

```text
Open Overview
  ↓
Check health and utilization summary
  ↓
Apply filters by Region / accelerator model / tenant / job
  ↓
Inspect Region × accelerator model matrix and TopN anomalies
  ↓
Click an anomalous accelerator, node, or job
  ↓
Open Resource Detail / Job Analysis Drawer
  ↓
Inspect timeline, trends, events, and similar-metric explanations
  ↓
Acknowledge alert, save view, export analysis, or jump to remediation action
```

---

## 4. Information Architecture

### 4.1 SPA Top-Level Tabs

| Tab | Name | Primary Users | Main Questions Answered |
|---|---|---|---|
| Overview | Overview | SRE / resource operations | Is it healthy, where is the anomaly, and where is waste? |
| Resources | Compute Resources | SRE / chip adaptation | What are the details of individual accelerators, nodes, Regions, and models? |
| Jobs | Training Jobs | Training engineers | Where is the job slow, and is any single accelerator dragging it down? |
| Trends | Trend Analysis | Platform admins / resource operations | What are the time trends across Regions, models, and tenants? |
| Alerts | Alert Events | SRE | Which alerts need action, and have they recurred historically? |
| Cost & Capacity | Cost & Capacity | FinOps / managers | How are card-hours, idle costs, queues, and capacity watermarks? |
| Settings | Metrics & Configuration | Platform admins | How are metric dictionary, thresholds, collection profiles, and view templates configured? |

### 4.2 Page Hierarchy

```text
Global Shell
├─ Top Bar: product name, global search, time range, refresh, export, user view
├─ Left Rail: Region/workspace shortcuts, favorite views, recently visited
├─ Page Header: current tab title, health summary, global filters
├─ Tab Content
│  ├─ Summary Cards
│  ├─ Matrix / Chart Cards
│  ├─ TopN / Table Cards
│  └─ Detail Drawer / Modal
└─ Toast / Alert Center
```

---

## 5. Unified Data Model

### 5.1 Core Objects

| Object | Description | Key Fields |
|---|---|---|
| Region | Geography, supporting cloud-provider Regions and self-built datacenter Regions | `region_id`, `region_name`, `cloud_provider`, `timezone`, `status` |
| Cluster | A cluster within a single Region | `cluster_id`, `region_id`, `k8s_version`, `network_type`, `storage_type` |
| Node | Physical machine or bare-metal instance | `node_id`, `cluster_id`, `rack_id`, `hostname`, `instance_type`, `os`, `kernel`, `driver_version` |
| Accelerator | Unified abstraction for one AI accelerator card | `accelerator_id`, `node_id`, `vendor`, `model`, `device_index`, `uuid`, `memory_total_gb`, `power_limit_w`, `health_status` |
| AcceleratorType | Accelerator model metadata | `vendor`, `model`, `architecture`, `memory_type`, `memory_total_gb`, `peak_flops`, `interconnect`, `adapter_type` |
| Job | Training job | `job_id`, `job_name`, `framework`, `parallel_strategy`, `tenant_id`, `user_id`, `status`, `start_time` |
| Pod / Container | Kubernetes runtime entity | `namespace`, `pod_name`, `container_name`, `node_id`, `job_id` |
| Metric | Metric definition | `metric_id`, `name`, `unit`, `type`, `layer`, `priority`, `scope`, `source`, `formula`, `help_text` |
| Alert | Alert event | `alert_id`, `severity`, `metric_id`, `resource_ref`, `status`, `first_seen`, `last_seen` |

### 5.2 Standard Labels / Dimensions

After entering the query layer, all metrics must be mapped to unified labels as much as possible. To control time-series cardinality, dynamic strings must not be added to TSDB labels arbitrarily.

| Dimension Category | Standard Fields | Description |
|---|---|---|
| Geography | `region_id`, `zone_id`, `cluster_id` | Basis for cross-Region aggregation. |
| Physical location | `rack_id`, `node_id`, `hostname` | Used to locate hardware and topology issues. |
| Accelerator | `accelerator_id`, `device_index`, `vendor`, `model`, `architecture` | Unified support for GPU/PPU/NPU/ASIC. |
| Runtime entity | `namespace`, `pod_name`, `container_name`, `process_id` | Used to drill down from accelerator to job process. |
| Job | `job_id`, `job_name_hash`, `framework`, `parallel_strategy` | Raw `job_name` does not enter labels to avoid high cardinality; raw names are stored in metadata. |
| Tenant | `tenant_id`, `workspace_id`, `user_id`, `queue_name` | Cost, quota, and fairness analysis. |
| Network | `nic_id`, `switch_id`, `network_type`, `fabric_id` | RoCE/IB/NVLink/NVSwitch. |
| Storage | `storage_type`, `bucket_id_hash`, `fs_id`, `mount_id` | Data loading and checkpoint. |
| Metric governance | `metric_id`, `priority`, `collection_profile`, `source_adapter` | Metric dictionary and collection policy. |

### 5.3 Metric Definition Schema

```json
{
  "metric_id": "accelerator.utilization.gpu.pct",
  "display_name": "Accelerator Compute Utilization",
  "unit": "%",
  "metric_type": "gauge",
  "layer": "hardware",
  "priority": "P0",
  "scope": ["accelerator", "pod", "job", "region"],
  "applicable_vendors": ["nvidia", "aliyun_ppu", "generic"],
  "default_aggregation": "time_weighted_avg",
  "supported_aggregations": ["avg", "max", "min", "p95", "topn", "bottomn"],
  "default_resolution": "5s",
  "raw_sources": ["dcgm_exporter", "nvml", "ppu_sdk_exporter"],
  "formula": "vendor_adapter.normalized_compute_busy_pct",
  "similar_metrics": [
    "accelerator.sm.occupancy.pct",
    "training.mfu.pct",
    "accelerator.tensor_core.utilization.pct"
  ],
  "tooltip": {
    "definition": "The proportion of the sampling window during which accelerator compute units are busy; used to determine whether the card is being used by a workload.",
    "difference": "Different from MFU: MFU measures actual model FLOPs divided by theoretical peak FLOPs. High GPU utilization does not necessarily mean high model efficiency.",
    "caveat": "Different vendors define busy differently. For cross-model comparison, prefer normalized metrics and same-model grouping."
  }
}
```

---

## 6. Multi-Region and Multi-Accelerator Adaptation Design

### 6.1 Multi-Region Collection and Query Architecture

```text
Region A Cluster(s)                       Region B Cluster(s)
┌─────────────────────┐                  ┌─────────────────────┐
│ node exporter        │                  │ node exporter        │
│ dcgm / ppu exporter  │                  │ dcgm / ppu exporter  │
│ kube-state-metrics   │                  │ kube-state-metrics   │
│ training hook        │                  │ training hook        │
└─────────┬───────────┘                  └─────────┬───────────┘
          │ scrape / OTLP / remote_write             │
          ▼                                           ▼
┌─────────────────────┐                  ┌─────────────────────┐
│ Regional Prometheus │                  │ Regional Prometheus │
│ short retention     │                  │ short retention     │
└─────────┬───────────┘                  └─────────┬───────────┘
          │ remote write / sidecar                    │
          └──────────────────┬────────────────────────┘
                             ▼
               ┌───────────────────────────┐
               │ Global Metrics Query Layer │
               │ Thanos / Mimir compatible  │
               └─────────────┬─────────────┘
                             ▼
               ┌───────────────────────────┐
               │ Monitoring API Gateway     │
               │ metadata + query + alert   │
               └─────────────┬─────────────┘
                             ▼
                       SPA Frontend
```

### 6.2 Multi-Region Product Rules

| Rule | Description |
|---|---|
| Default global view | When the user opens the page, they see a summary of all authorized Regions by default. |
| Region multi-select | Filters in every tab support single-select, multi-select, exclusion, and favorite Regions. |
| Region-level degradation | If a Region query times out, it does not block the global page; cards show a `partial data` state. |
| Unified timezone | The backend stores data in UTC; the frontend displays in the user’s timezone and also allows switching to a Region’s local time. |
| Region dimension always visible | All TopN, Trend, and Matrix results retain Region identity by default to avoid cross-Region misinterpretation. |
| Weighted rollups | Multi-Region rollups must not use simple averages; they use `sample_count`, `card_count`, or `allocated_card_seconds` for weighting. |

### 6.3 Accelerator Model Adaptation Matrix

| Accelerator Model | Vendor | Adaptation Method | Key Capability Metadata | Metric Design Notes |
|---|---|---|---|---|
| NVIDIA H200 | NVIDIA | DCGM Exporter + NVML + NCCL + Kubernetes | HBM3e 141GB, memory bandwidth 4.8TB/s, Hopper architecture | Supports high-frequency GPU/memory/power/temperature/Xid/ECC/NVLink metrics; suitable for training efficiency and communication analysis. |
| NVIDIA RTX PRO 5000 Blackwell | NVIDIA | DCGM/NVML subset + node exporter | Blackwell, 48GB/72GB GDDR7 ECC, memory bandwidth 1344GB/s, 300W | As a professional/workstation card, some datacenter capabilities should be shown in gray release according to actual driver and DCGM support. |
| Alibaba Cloud Zhenwu 810E / M890 PPU | Alibaba Cloud / T-Head | PPU SDK Exporter + PAI/ACS resource metadata + Kubernetes | 810E 96GB, M890 144GB; inter-chip interconnect 700/800GB/s; compatible with mainstream AI frameworks and PAI/ACS scenarios | Do not force NVIDIA-only fields such as Xid and NVLink; store native fields in `adapter_specific`, then map them to generic metrics. |
| Generic Accelerator | Other GPU/NPU/ASIC | OpenTelemetry / Prometheus exporter adapter | User-configured peak compute, memory, power, and interconnect type | Support P0/P1 common metrics first; expert metrics expand according to adapter capability. |

### 6.4 Adapter Design

```text
Raw Vendor Metrics
  ↓
Vendor Adapter
  ├─ metric name normalize
  ├─ unit normalize
  ├─ label normalize
  ├─ missing field handling
  ├─ capability detection
  └─ metric dictionary registration
  ↓
Unified Metric Store
```

The adapter must implement:

| Method | Description |
|---|---|
| `discover()` | Discover nodes, accelerators, drivers, SDKs, topology, and collectible metrics. |
| `normalizeMetric()` | Map raw metrics to platform-standard metrics. |
| `capability()` | Return which metrics are supported, unsupported, or estimated for the current accelerator model. |
| `healthCheck()` | Determine whether exporter, driver, and SDK are working. |
| `explain()` | Return metric semantics for Tooltip and metric dictionary. |

---

## 7. Productized Metric Scope

### 7.1 Three-Level Metric Display Strategy

| Level | Name | Goal | Display Location | Metric Count Strategy |
|---|---|---|---|---|
| L0 | Homepage core metrics | Quickly judge overall state | Overview first-screen Summary Cards | No more than 12 |
| L1 | Standard analysis metrics | Daily troubleshooting and capacity operations | Resources / Jobs / Trends | 20–40 per page, grouped |
| L2 | Expert diagnostic metrics | Deep performance optimization and chip adaptation | Metric Explorer / Expert Mode | Hidden by default, opened on demand |

### 7.2 L0 Homepage Core Metrics

| Metric | Semantics | Default Aggregation | Main Value | Priority |
|---|---|---|---|---|
| Total cards | Number of managed accelerator cards | count | Capacity baseline | P0 |
| Available cards / availability rate | Number and ratio of cards where `health_status=healthy` | count / ratio | Hardware health | P0 |
| Allocated cards / allocation rate | Number of cards bound to Job/Pod | count / ratio | Scheduling watermark | P0 |
| Active training cards | Cards with training workload and compute utilization above threshold | count | Distinguish “occupied but unused” | P0 |
| Average compute utilization | Sample-weighted average by card | weighted avg | Resource usage | P0 |
| Average memory utilization | Weighted by card memory capacity | weighted avg | Memory pressure | P0 |
| P0 alerts | Current unrecovered P0 alerts | count | On-call entry point | P0 |
| Hardware error events | Xid/ECC/offline/PPU-native hardware errors | increase | Failure localization | P0 |
| Thermal/power-limited cards | Cards hitting temperature, power limit, or thermal throttle | count | Performance degradation | P1 |
| Training throughput | Aggregated Tokens/s or Samples/s | sum / avg | Training output | P1 |
| Low-utilization TopN | Allocated cards/jobs with low compute utilization | topN | Waste localization | P1 |
| Idle card-hour cost | Estimated card-hours for unallocated or low-utilization cards | sum | Cost governance | P1 |

### 7.3 L1 Standard Analysis Metrics

#### 7.3.1 Hardware and System

| Category | Metrics | Default Granularity | Default Refresh | Page |
|---|---|---:|---:|---|
| Accelerator utilization | Compute utilization, Tensor/matrix unit utilization, memory utilization, memory bandwidth | Accelerator / Job | 5s | Overview / Resources / Jobs |
| Accelerator health | Temperature, power, power-limit hit, thermal throttle, fan/liquid-cooling state | Accelerator / Node | 5s~15s | Resources / Alerts |
| Hardware errors | Xid, ECC, offline card, NVLink/PCIe errors, PPU-native error code | Accelerator / Node | event | Resources / Alerts |
| CPU/memory | CPU utilization, IOWait, system memory, NUMA imbalance, OOM Kill | Node / Pod | 15s | Resources / Jobs |
| Kubernetes runtime | Pending time, scheduling failures, restarts, Exit Code, resource requests/limits | Pod / Job | event~15s | Jobs / Alerts |

#### 7.3.2 Network and Storage

| Category | Metrics | Default Granularity | Default Refresh | Page |
|---|---|---:|---:|---|
| Intra-node interconnect | NVLink/NVSwitch/PCIe bandwidth, errors, link status | Accelerator / Node | 5s | Resources / Jobs |
| Inter-node network | RoCE/IB bandwidth, PFC/ECN, port down, bit errors, P99 latency | NIC / Node / Job | 5s~15s | Resources / Trends |
| Collective communication | AllReduce/AllGather/ReduceScatter latency, bandwidth efficiency, communication wait ratio | Job / Node | step~5s | Jobs |
| Data loading | DataLoader iteration time, prefetch queue, CPU→GPU/PPU copy, IO wait | Job / Pod | step~5s | Jobs |
| Checkpoint | Save/restore time, file size, write bandwidth, async queue depth, failures | Job | event~5s | Jobs / Alerts |

#### 7.3.3 Training Efficiency and Business Operations

| Category | Metrics | Default Granularity | Default Refresh | Page |
|---|---|---:|---:|---|
| Step efficiency | Step time, P50/P95/P99, breakdown of forward/backward/optimizer/communication/data loading | Job | step | Jobs |
| Throughput | Tokens/s, Samples/s, per-card throughput, cluster total throughput | Job / Accelerator | step | Overview / Jobs |
| MFU / compute efficiency | MFU, achieved TFLOPS, matrix multiplication efficiency | Job / Accelerator | step | Jobs / Trends |
| Waiting and idleness | GPU/PPU idle, data wait, communication wait, synchronization barrier wait | Job / Accelerator | step | Jobs |
| Training anomalies | Loss spike, NaN/Inf, gradient explosion/vanishing, LR anomaly | Job | event | Jobs / Alerts |
| Cost | Card-hours, idle card-hours, cost per million tokens, Goodput, budget burn | Job / User / Tenant | 60s~step | Cost & Capacity |
| Scheduling | Queue depth, queue time, resource fragmentation, preemption, quota utilization | Cluster / Tenant | 60s | Overview / Cost & Capacity |

### 7.4 L2 Expert Diagnostic Metrics

Hidden by default and opened only when:

1. The user switches to `Expert Mode`.
2. A P1/P2 alert recommends opening it.
3. A training job enters the performance tuning view.
4. A new accelerator model or PPU is in gray-release adaptation.

| Expert Metric | Use Case | Collection Overhead Control |
|---|---|---|
| SM Occupancy / Warp Occupancy | CUDA kernel inefficiency localization | Not collected globally by default; enabled only for selected jobs |
| L1/L2/L3 Cache / TLB Miss / IPC | CPU/memory bottleneck localization | Sampled in collection windows |
| Operator latency Top20 / memory Top20 | Model performance optimization | PyTorch Profiler sampled according to schedule |
| NCCL Debug / algorithm selection / channel information | Collective communication anomaly localization | Enabled only for anomalous jobs to avoid log flooding |
| eBPF syscall / TCP retransmission / block IO latency | System-level bottleneck localization | Event-triggered or short-window sampling |
| Memory fragmentation / allocator details | OOM and memory leak diagnosis | Requires framework Hook support |

---

## 8. Metric Definitions and Differences from Similar Metrics

### 8.1 Core Metrics That Must Have Built-in Tooltips

| Metric | Definition | Easily Confused With | Difference |
|---|---|---|---|
| Compute utilization | Proportion of sampling window during which accelerator compute units are busy | MFU, SM Occupancy | High utilization means the card is busy, not that model compute is efficient; MFU is closer to effective training compute. |
| MFU | Actual model FLOPs / theoretical device peak FLOPs | Compute utilization, Tokens/s | MFU requires model FLOPs and model-specific peak metadata; it can compare job efficiency, but cross-model comparison requires caution. |
| Memory utilization | Used memory / total memory | Memory bandwidth utilization, memory fragmentation | Full memory does not necessarily mean slow; high bandwidth may indicate memory access bottleneck; high fragmentation can cause OOM. |
| Memory bandwidth utilization | Actual memory read/write bandwidth / theoretical bandwidth | Memory utilization | Memory utilization is capacity; bandwidth utilization is throughput pressure. |
| GPU/PPU idle time | Proportion of a training step during which the device has no effective kernel/operator execution | Communication wait, data wait | Idle is the outcome; communication/data wait are causal breakdowns. |
| Communication wait ratio | Proportion of a step spent waiting for collective communication or synchronization barriers | NCCL AllReduce latency | A single slow communication operation may not affect total training; high wait ratio means it blocks training. |
| DataLoader time | Time spent per step on data reading, decoding, and preprocessing | IOWait, CPU utilization | DataLoader is a training perspective; IOWait/CPU are system perspectives. |
| Thermal throttle event | Frequency or event that a device is downclocked or power-limited due to thermal policy | Temperature, power | High temperature is a state; thermal throttle is a performance-impacting event. |
| Card-hours | Number of allocated or used accelerator cards × time | Idle card-hours, Goodput | Card-hours is a cost metric; Goodput measures the ratio of effective training time. |
| Resource fragmentation ratio | Ratio of remaining resources that cannot be scheduled due to model/topology/quota constraints | Idle card count | Having idle cards does not mean a large job can be scheduled; fragmentation explains “cards exist but jobs queue.” |

### 8.2 Tooltip Content Template

```text
Metric name: MFU
Definition: Actual model FLOPs / theoretical peak FLOPs of the current accelerator model.
Unit: %
Default aggregation: Time-weighted average by step within a job; across jobs, do not directly average by default, use token- or step-weighting.
Differences from similar metrics:
- Different from GPU utilization: GPU utilization reflects device busy/idle state; MFU reflects effective model compute efficiency.
- Different from Tokens/s: Tokens/s is business throughput and is affected by batch size, sequence length, and parallel strategy.
Collection source: Training Hook + accelerator model peak metadata.
Common anomaly: High GPU utilization but low MFU usually indicates low kernel efficiency, communication wait, padding waste, or an unreasonable parallel strategy.
```

---

## 9. Filter Design

### 9.1 Filter Layers

| Layer | Filter | Scope | UI Form |
|---|---|---|---|
| Global filters | Time range, Region, Cluster, tenant, accelerator model | All tabs | Top Filter Bar |
| Page filters | Business filters for the current tab, such as job status, alert severity, cost semantics | Current tab | Top of tab content |
| Card filters | Group by, TopN, threshold for a single card | Current card | Card header mini controls |
| Chart interaction filters | Brush time range, legend toggles, point clicks | Current chart or linked Drawer | In-chart interaction |

### 9.2 Dimension Filters

| Dimension | Interaction | Parameter Name | Example |
|---|---|---|---|
| Region | Multi-select, favorite, exclude | `region_ids` | `['cn-hangzhou', 'cn-wulanchabu']` |
| Cluster | Multi-select, search | `cluster_ids` | `['train-prod-a']` |
| Accelerator model | Multi-select, grouped by vendor | `accelerator_models` | `['H200', 'RTX_PRO_5000_BLACKWELL', 'ZHENWU_810E']` |
| Vendor | Multi-select | `vendors` | `['nvidia', 'aliyun_ppu']` |
| Health status | Quick chips | `health_status` | `['warning', 'critical']` |
| Node | Search, multi-select | `node_ids` | `['node-123']` |
| Job | Search, multi-select, recently visited | `job_ids` | `['job-abc']` |
| Tenant/user | Multi-select | `tenant_ids`, `user_ids` | `['team-a']` |
| Runtime framework | Multi-select | `frameworks` | `['Megatron', 'DeepSpeed', 'FSDP']` |
| Parallel strategy | Multi-select | `parallel_strategies` | `['DP', 'TP', 'PP', 'ZeRO']` |
| Network type | Multi-select | `network_types` | `['RoCE', 'IB', 'NVLink']` |

### 9.3 Metric Value Filters

Metric value filters are used to “find problems from massive single-card/job data” and support conditional expressions:

```text
metric(operator)value
metric BETWEEN min AND max
metric RATE_GT value PER window
metric INCREASE_GT value PER window
metric DEVIATE_GT baseline_pct
metric RANK_TOP n BY metric
```

Common presets:

| Preset Name | Condition Expression | Typical Use |
|---|---|---|
| Allocated but low utilization | `allocated=true AND accelerator.utilization.compute.pct < 20 FOR 15m` | Find occupied-but-unused resources |
| High memory, low compute | `memory.used.pct > 80 AND compute.utilization.pct < 30 FOR 10m` | Find data/communication/waiting issues |
| Thermal throttle | `thermal.throttle.events > 0 OR power.limit.hit.pct > 5` | Find performance downclocking |
| Communication bottleneck | `training.wait.communication.pct > 25 OR nccl.allreduce.duration.p95 > baseline*1.2` | Find NCCL/network issues |
| IO bottleneck | `training.wait.data.pct > 20 OR dataloader.iteration.ms.p95 > baseline*1.2` | Find data loading issues |
| Hardware risk | `xid.errors.increase > 0 OR ecc.uncorrectable.increase > 0 OR device.offline.events > 0` | Find faulty cards |
| Cost anomaly | `cost.per_million_tokens > baseline*1.3 OR goodput.pct < 70` | Find training cost anomalies |

### 9.4 Explainability of Filter Results

After each filter is applied, the page displays a natural-language summary:

```text
Current filter: Past 6 hours, Hangzhou + Ulanqab, H200 + Zhenwu 810E, allocated but compute utilization < 20% for 15 minutes.
Matched: 143 cards, covering 18 jobs, 42 nodes, and 3 tenants.
```

---

## 10. Aggregation and Trend Analysis

### 10.1 Aggregation Functions

| Function | Applicable Metrics | Description |
|---|---|---|
| `sum` | Card-hours, error counts, throughput, cost | Cumulative metrics. |
| `avg` | Utilization, temperature, power | Simple dimensional average; consider whether weighting is needed. |
| `weighted_avg` | Cross-model utilization, MFU, memory utilization | Weighted by sample count, card-hours, memory capacity, or tokens. |
| `min/max` | Temperature, power, memory, Step time | Extreme value localization. |
| `p50/p95/p99` | Step time, latency, DataLoader, communication time | Tail analysis. |
| `rate` | Counter-type errors, network packets, IO bytes | Rate per unit time. |
| `increase` | Xid/ECC/OOM/restart | Increment within a time window. |
| `topn/bottomn` | Utilization, cost, alert count, wait ratio | Ranking. |
| `distribution` | Utilization distribution, temperature distribution, queue time distribution | Histogram/box plot. |
| `baseline_deviation` | Step time, Tokens/s, MFU, communication time | Compare with historical or peer baseline. |

### 10.2 Dimension Rollups

| Rollup Perspective | Example Question | Default Display |
|---|---|---|
| Region | Which Region has more failures or lower utilization? | Region comparison Card |
| Accelerator model | How do H200 vs PPU vs RTX PRO 5000 perform differently? | Model matrix + trend |
| Tenant | Which team has high card-hours but low efficiency? | Tenant TopN |
| Job | Which jobs are slowing the cluster down? | Job TopN |
| Node | Which nodes have concentrated anomalies? | Node TopN + heatmap |
| Time | Is today worse than yesterday? | Trend chart + baseline deviation |
| Framework/parallel strategy | How do DeepSpeed/FSDP/Megatron differ in efficiency? | Training efficiency grouped chart |

### 10.3 Trend Analysis

Trend analysis must cover two categories:

1. **Single-accelerator detailed time series**: fixed `accelerator_id`, displaying compute utilization, memory, temperature, power, errors, and associated Job/Pod.
2. **Dimension-rollup time series**: time series aggregated by `region / model / tenant / job / node / framework`.

Trend chart interactions:

| Interaction | Description |
|---|---|
| Time range | 15m, 1h, 6h, 24h, 7d, custom. |
| Resolution | Auto, 1s, 5s, 15s, 1m, 5m. |
| Group By | Region, accelerator model, Job, tenant, Node, framework. |
| Compare | Same time yesterday, previous hour, peer model baseline. |
| Brush | Select an anomalous time period and automatically feed it into the event list below. |
| Overlay | Overlay alerts, job phases, checkpoints, Pod restarts, and scheduling events. |

### 10.4 Aggregation Formula Examples

#### Cross-Region Compute Utilization

```text
global_compute_util =
  sum(region_compute_util_avg * region_active_card_sample_count)
  / sum(region_active_card_sample_count)
```

#### Memory Utilization

```text
memory_used_pct =
  sum(memory_used_bytes) / sum(memory_total_bytes) * 100
```

#### Card-Hours

```text
accelerator_hours =
  sum(allocated_accelerator_count_per_interval * interval_seconds) / 3600
```

#### Goodput

```text
goodput_pct =
  useful_training_time_seconds / wall_clock_allocated_seconds * 100
```

#### MFU

```text
mfu_pct =
  achieved_model_flops_per_second / accelerator_peak_flops_for_precision * 100
```

---

## 11. Page and Feature Design

## 11.1 Overview

### 11.1.1 Page Goal

Enable users to know within 10 seconds: whether the overall system is healthy, which Region/model/job has issues, whether resources are wasted, and where to click for drill-down.

### 11.1.2 Page Structure

```text
Overview
├─ Hero Summary Band
│  ├─ Global health title
│  ├─ Time range / refresh status
│  └─ 4 main KPIs: Available cards, active cards, average utilization, P0 alerts
├─ Global Filter Bar
├─ Health & Utilization Cards
├─ Region × Accelerator Model Matrix
├─ TopN Cards
│  ├─ Abnormal accelerators TopN
│  ├─ Low-utilization jobs TopN
│  ├─ Thermal/power-risk nodes TopN
│  └─ Cost waste TopN
└─ Event Timeline
```

### 11.1.3 Card Design

| Card | Content | On Click |
|---|---|---|
| Global Health | Healthy card ratio, anomalous card count, P0/P1 alert count | Open Alerts with P0/P1 filters applied |
| Utilization | Average compute utilization, memory utilization, active cards | Open Trends, group by Region |
| Availability | Total cards, available cards, unavailable cards, offline events | Open Resources filtered to unhealthy |
| Cost Waste | Idle card-hours, low-utilization card-hours, estimated wasted cost | Open Cost & Capacity |
| Region × Card Matrix | Health, utilization, and allocation rate for each Region/model | Click cell to enter Resources with filters applied |
| Top Abnormal Accelerators | Anomalous single-accelerator TopN | Open single-accelerator Detail Drawer |
| Top Slow Jobs | Step-time degradation / communication wait / IO wait TopN | Open Job Detail Drawer |

---

## 11.2 Resources: Compute Resources Page

### 11.2.1 Page Goal

Support viewing resource details at Region, Cluster, Node, and single-accelerator levels, and locating hardware and system issues.

### 11.2.2 Page Structure

```text
Resources
├─ Resource Filter Bar
├─ Inventory Summary Cards
├─ Resource Table
│  ├─ Layered Region / Cluster / Node / Accelerator view
│  ├─ Column configuration
│  └─ Metric value filters
├─ Resource Trend Panel
└─ Accelerator Detail Drawer
```

### 11.2.3 Resource Table Fields

| Field | Description |
|---|---|
| Status | Healthy / Warning / Critical / Offline |
| Region / Cluster / Node | Location dimensions |
| Accelerator model | H200 / RTX PRO 5000 / Zhenwu 810E / Zhenwu M890 / custom |
| Vendor | NVIDIA / Alibaba PPU / Generic |
| Current Job | Currently bound job, clickable |
| Compute utilization | Current value + past 15m sparkline |
| Memory utilization | Current value + peak |
| Temperature / Power | Current value + threshold state |
| Errors | Xid/ECC/offline/PPU error count |
| Network | NVLink/PCIe/NIC state |
| Collection status | exporter healthy / stale / missing |

### 11.2.4 Single-Accelerator Detail Drawer

Drawer width is 560px and slides out from the right. Content:

1. Accelerator identity: `accelerator_id`, vendor, model, uuid, Region, Node, device index.
2. Status summary: health, current Job, collection status, recent events.
3. Core curves: compute utilization, memory, memory bandwidth, temperature, power.
4. Runtime binding: Pod, Container, Process, Job, tenant.
5. Event timeline: alerts, Xid/ECC, offline card, Pod restart, checkpoint.
6. Similar-metric explanations: GPU utilization vs MFU vs SM Occupancy.
7. Actions: copy resource ID, open Job, create alert rule, export time window, mark maintenance.

---

## 11.3 Jobs: Training Job Analysis Page

### 11.3.1 Page Goal

Enable training engineers to determine where a job is slow: compute, communication, data, checkpoint, scheduling, hardware anomaly, or code/model behavior.

### 11.3.2 Page Structure

```text
Jobs
├─ Job Search / Filter
├─ Job Summary Cards
│  ├─ Status / runtime
│  ├─ Tokens/s / Samples/s
│  ├─ Step time P50/P95/P99
│  ├─ MFU / Goodput
│  └─ Cost / card-hours
├─ Step Time Breakdown
├─ Accelerator Skew Matrix
├─ Communication & IO Analysis
├─ Loss / LR / NaN Trend
└─ Job Event Timeline
```

### 11.3.3 Step-Time Breakdown

| Breakdown Item | Source | Purpose |
|---|---|---|
| Forward | Framework Hook / Profiler | Model forward time |
| Backward | Framework Hook / Profiler | Backpropagation time |
| Optimizer | Framework Hook | Optimizer time |
| Communication | NCCL / Framework Hook | Gradient synchronization and collective communication |
| Data Loading | DataLoader Hook / IO metrics | Data bottleneck |
| Checkpoint | Checkpoint Hook | Save/restore impact |
| Idle / Barrier | Runtime Hook | Synchronization wait and long-tail card impact |

### 11.3.4 Accelerator Skew Matrix

Rows are `node_id`, columns are `device_index`, and each cell displays:

- Step-time deviation relative to job median.
- Compute utilization.
- Communication wait ratio.
- Data wait ratio.
- Anomaly event badge.

Color rules:

| State | Condition | Color |
|---|---|---|
| Normal | Deviation < 10% | mint/green |
| Slight slowdown | 10%~20% | yellow |
| Obvious slowdown | 20%~50% | orange |
| Severe slowdown | >50% or P0 event exists | red |

---

## 11.4 Trends: Trend Analysis Page

### 11.4.1 Page Goal

Support time-trend comparison across Regions, accelerator models, tenants, and jobs, covering both single-accelerator details and aggregated trends.

### 11.4.2 Page Structure

```text
Trends
├─ Query Builder
│  ├─ Metric Selector
│  ├─ Dimension Filters
│  ├─ Metric Value Filters
│  ├─ Group By
│  ├─ Aggregation
│  └─ Compare Baseline
├─ Trend Chart Card
├─ Distribution Card
├─ TopN Over Time Card
└─ Result Table
```

### 11.4.3 Query Example

```text
Past 24 hours, Region=Hangzhou/Ulanqab, accelerator model=H200/Zhenwu810E,
group by card_type + region, inspect average compute utilization, P95 Step time, and hardware error count.
```

### 11.4.4 Chart Capabilities

| Chart | Use |
|---|---|
| Line chart | Multi-Region/model trend comparison |
| Area chart | Cumulative trends for card-hours, cost, throughput |
| Heatmap | Node/card load distribution |
| Box plot | Step time / utilization distribution |
| Rank-change chart | How TopN jobs/tenants change over time |
| Scatter plot | Utilization vs cost, MFU vs Tokens/s |

---

## 11.5 Alerts: Alert Events Page

### 11.5.1 Page Goal

Complete alert discovery, acknowledgement, localization, related-metric inspection, recurrence judgment, and rule optimization.

### 11.5.2 Alert List Fields

| Field | Description |
|---|---|
| Severity | P0/P1/P2/P3 |
| Status | Firing / Acknowledged / Silenced / Resolved |
| Alert name | Such as `AcceleratorOffline`, `XidError`, `LowUtilizationAllocated` |
| Resource | Region / Node / Accelerator / Job |
| Current value | Metric value when triggered |
| Threshold | Fixed threshold or baseline deviation |
| First seen | `first_seen` |
| Last seen | `last_seen` |
| Related events | Pod restart, checkpoint, network event |
| Suggested action | Open accelerator details, isolate node, contact tenant, scale out, etc. |

### 11.5.3 Alert Rule Templates

| Template | Condition | Default Severity |
|---|---|---|
| Single accelerator offline | `device.offline.events > 0` | P0 |
| Uncorrectable ECC | `ecc.uncorrectable.increase > 0` | P0 |
| Xid error | `xid.errors.increase > 0` | P0/P1 |
| Thermal throttle | `thermal.throttle.events > 0 FOR 5m` | P1 |
| Allocated low utilization | `allocated=true AND compute.utilization.pct < 20 FOR 30m` | P1 |
| Abnormal communication wait | `training.wait.communication.pct > 30 FOR 10m` | P1 |
| DataLoader anomaly | `training.wait.data.pct > 25 FOR 10m` | P1 |
| Queue backlog | `queue.pending_time.p95 > SLO FOR 15m` | P1/P2 |
| Cost over budget | `cost.budget_used.pct > threshold` | P2 |

---

## 11.6 Cost & Capacity Page

### 11.6.1 Page Goal

Convert compute consumption into operating metrics: card-hours, idle card-hours, low-utilization cost, Goodput, queues, resource fragmentation, and capacity watermarks.

### 11.6.2 Core Cards

| Card | Metrics | Drill-Down |
|---|---|---|
| Card-hours | GPU/PPU card-hours, allocated card-hours, active card-hours | By Region/tenant/job |
| Waste | Idle card-hours, allocated low-utilization card-hours, estimated waste | Top inefficient jobs/tenants |
| Goodput | Ratio of effective training time | Job details |
| Queue | Queue time P50/P95, queue depth | Scheduling failure reasons |
| Fragmentation | Resource fragmentation ratio, unschedulable remaining resources | Region/model/topology |
| Capacity Watermark | 7d/30d watermark, peak, forecast | Scaling recommendations |

---

## 11.7 Settings: Metrics and Configuration Page

### 11.7.1 Settings Items

| Configuration | Description |
|---|---|
| Metric dictionary | Metric enablement, name, unit, definition, similar metrics, source, priority. |
| Collection Profile | Basic / Standard / Expert; configurable by Region/model/tenant. |
| Threshold templates | Global thresholds, per-model thresholds, per-tenant thresholds, baseline rules. |
| View templates | Saved views for Overview, Job, and Resource pages. |
| Adapter management | Health and mapping for NVIDIA, PPU, and custom exporters. |
| Permissions | Which users can view cost, tenant, single-accelerator details, and alert actions. |

### 11.7.2 Collection Profiles

| Profile | Target Scenario | Collection Content | Default Policy |
|---|---|---|---|
| Basic | On-call and capacity | P0 core: health, utilization, memory, temperature, power, errors, Kubernetes state | Enabled globally |
| Standard | Daily troubleshooting | P1: network, communication, Step time, throughput, data loading, checkpoint, cost | Enabled by default for training clusters |
| Expert | Performance tuning | P2: Profiler, operators, SM/Warp, eBPF, NCCL debug | Enabled by job/time window |

---

# 12. Independent UI Design Chapter

## 12.1 General Design Style Principles

The visual style fully follows Notion: white canvas, soft gray surface, low-saturation pastel cards, deep navy hero band, purple primary button, Notion Sans font, 8px rectangular buttons, 12px card radius, fine hairline borders, and light shadows.

### 12.1.1 Design Tokens

| Token | Value | Use |
|---|---|---|
| `colors.primary` | `#5645d4` | Main CTA and selected-state emphasis; not used as a large-area background. |
| `colors.brand-navy` | `#0a1530` | Overview top hero summary band. |
| `colors.canvas` | `#ffffff` | Main page and card background. |
| `colors.surface` | `#f6f5f4` | Page background, search bar, light sections. |
| `colors.hairline` | `#e5e3df` | Cards, tables, separators. |
| `colors.ink` | `#1a1a1a` | Primary body text. |
| `colors.charcoal` | `#37352f` | Titles and important text. |
| `colors.steel` | `#787671` | Secondary text. |
| `colors.semantic-success` | `#1aae39` | Normal/recovered. |
| `colors.semantic-warning` | `#dd5b00` | Warning. |
| `colors.semantic-error` | `#e03131` | Severe error. |

### 12.1.2 Typography

```css
font-family: "Notion Sans", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

| Level | Font Size | Weight | Line Height | Use |
|---|---:|---:|---:|---|
| Page Title | 36px | 600 | 1.20 | Tab page title |
| Section Title | 22px | 600 | 1.30 | Card group title |
| Card Title | 16px | 600 | 1.40 | Single-card title |
| Metric Value | 28px | 600 | 1.15 | KPI value |
| Body | 14px | 400 | 1.50 | Tables, descriptions |
| Caption | 12~13px | 500/600 | 1.40 | Badges, explanations |

### 12.1.3 Border Radius and Borders

| Component | Radius | Border |
|---|---:|---|
| Button | 8px | Secondary uses `1px solid #c8c4be` |
| Card | 12px | `1px solid #e5e3df` |
| Input / Search | 8px | `1px solid #c8c4be`; focus `2px solid #5645d4` |
| Pill Tab | 9999px | inactive `1px solid #e5e3df` |
| Drawer | 16px top-left/bottom-left | `1px solid #e5e3df` |
| Badge | 9999px or 6px | none or light border |

---

## 12.2 Global Page Layout: Desktop 1440 × 900

### 12.2.1 Shell

```text
┌──────────────────────────────────────────────────────────────┐
│ Top Bar: 64px                                                │
├───────────────┬──────────────────────────────────────────────┤
│ Left Rail     │ Main Content                                 │
│ 248px         │ calc(100vw - 248px)                          │
│               │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

### 12.2.2 Top Bar

| Attribute | Value |
|---|---|
| Height | 64px |
| Background | `#ffffff` |
| Border | bottom `1px solid #e5e3df` |
| Left | 32px logo, product name, current environment Badge |
| Center | Global search, width 420px, height 44px, background `#f6f5f4` |
| Right | Time range, refresh button, export button, user avatar |
| Font | 14px / 500 |

### 12.2.3 Left Rail

| Attribute | Value |
|---|---|
| Width | 248px |
| Background | `#fafaf9` |
| Border | right `1px solid #e5e3df` |
| Padding | 16px 12px |
| Sections | Favorites, Regions, Views, Recent Jobs |
| Item height | 36px |
| Item radius | 6px |
| Active background | `#f0eeec` |

### 12.2.4 Main Content

| Attribute | Value |
|---|---|
| Background | `#ffffff` |
| Max content width | 1280px |
| Horizontal padding | 32px |
| Top padding | 24px |
| Card gap | 16px |
| Grid | 12 columns, 16px gutter |

---

## 12.3 Pixel-Level Layout for Overview Page

```text
Main Content width: 1192px at 1440px viewport

Y=0     Top Bar 64
Y=64    Page scroll area
Y=88    Hero Band 180px
Y=292   Pill Tab Row 44px
Y=348   Filter Bar 56px
Y=420   KPI Cards Row 132px
Y=568   Matrix + TopN Row 360px
Y=944   Timeline Row 280px
```

### 12.3.1 Hero Summary Band

| Attribute | Value |
|---|---|
| Position | Top of main content |
| Size | Width 100%, height 180px |
| Background | `#0a1530` |
| Radius | 16px |
| Padding | 32px |
| Decoration | 8–12 pastel sticky dots in the top-right corner, opacity 0.9; they must not interfere with data readability |
| Title | 36px / 600 / white |
| Subtitle | 14px / `#a4a097` |
| Right side | Refresh state, data completeness Badge, current time range |

A white summary card in `workspace-mockup-card` style is placed on the right side inside the Hero:

| Attribute | Value |
|---|---|
| Size | 420px × 132px |
| Background | `#ffffff` |
| Radius | 12px |
| Shadow | `rgba(15,15,15,0.20) 0px 24px 48px -8px` |
| Content | 4 mini KPIs: Healthy, Active, Alerts, Waste |

### 12.3.2 Pill Tab Row

| Attribute | Value |
|---|---|
| Height | 44px |
| Top margin | 24px |
| Tab height | 32px |
| Inactive | Text `#787671`, border `#e5e3df`, radius 9999px |
| Active | Background `#000000`, text `#ffffff` |
| Tab gap | 8px |

### 12.3.3 Filter Bar

| Attribute | Value |
|---|---|
| Height | 56px |
| Background | `#f6f5f4` |
| Radius | 12px |
| Padding | 8px 12px |
| Components | Region Select, Card Type Select, Tenant Select, Metric Condition, Group By, Reset |
| Select height | 40px |
| Search input | 240px × 40px |
| Chip | 28px high, radius 9999px |

### 12.3.4 KPI Cards

Four main cards; each is `(1192 - 3*16)/4 = 286px` wide and 132px high.

| Element | Style |
|---|---|
| Card background | `#ffffff` |
| Border | `1px solid #e5e3df` |
| Radius | 12px |
| Padding | 20px |
| Title | 13px / 600 / `#787671` |
| Value | 28px / 600 / `#1a1a1a` |
| Delta | 13px badge, green/orange/red |
| Sparkline | bottom-right, 88px × 28px |

KPI card colors are used only for badges and small charts, not as large high-saturation backgrounds.

### 12.3.5 Matrix Card

| Attribute | Value |
|---|---|
| Size | 776px × 360px, spans 8 columns |
| Title | `Region × Card Type` |
| Header height | 40px |
| Cell | 96px × 64px |
| Cell content | Health rate, average utilization, P0 count |
| Color scale | pastel mint/yellow/peach/rose; no harsh red/green blocks |
| Click | Clicking a cell applies filters and opens Resources |

### 12.3.6 TopN Card

| Attribute | Value |
|---|---|
| Size | 400px × 360px, spans 4 columns |
| Tabs | Abnormal / Low Util / Slow Jobs / Cost |
| Row height | 44px |
| Row content | Rank, resource name, Region, metric value, trend arrow |
| Click | Opens Detail Drawer |

### 12.3.7 Detail Drawer

| Attribute | Value |
|---|---|
| Width | 560px |
| Height | 100vh |
| Position | right: 0, top: 0 |
| Background | `#ffffff` |
| Border | left `1px solid #e5e3df` |
| Shadow | `rgba(15,15,15,0.16) 0px 16px 48px -8px` |
| Header height | 72px |
| Content padding | 24px |
| Close button | 32px × 32px, ghost |
| API | When opened, fetch resource details, trends, events, and metric explanations |

---

## 12.4 Component Interactions and API Binding

### 12.4.1 General API Conventions

| Item | Convention |
|---|---|
| Base URL | `/api/v1/monitor` |
| Authentication | Inherits platform login state; all APIs validate workspace/tenant/resource permissions |
| Time parameters | `start_time`, `end_time` use ISO8601 UTC; frontend localizes display |
| Resolution | `resolution=auto|1s|5s|15s|1m|5m|1h` |
| Request method | Complex query conditions use POST uniformly; lightweight metadata uses GET |
| Response state | Every response includes `data_status: complete|partial|stale|empty` |
| Error handling | Region-level partial data does not block the global response |

### 12.4.2 Page Load and Global Interaction APIs

| Interaction | API Name | Method | Path | Function | Key Parameters |
|---|---|---|---|---|---|
| Open SPA | GetBootstrap | GET | `/bootstrap` | Get user permissions, default view, default time range, accessible Regions | `workspace_id` |
| Get Region list | ListRegions | GET | `/meta/regions` | Return accessible Regions and status | `workspace_id`, `include_status` |
| Get accelerator model list | ListAcceleratorTypes | GET | `/meta/accelerator-types` | Return vendor/model/capability | `region_ids[]`, `vendors[]` |
| Get metric dictionary | ListMetricDictionary | GET | `/metrics/dictionary` | Return metric definitions, units, tooltips, similar metrics | `layer`, `priority`, `vendor`, `model` |
| Global search | GlobalSearch | GET | `/search` | Search Job/Node/Accelerator/Alert | `q`, `types[]`, `limit` |
| Change time range | QueryOverviewSummary | POST | `/overview/summary` | Refresh Overview KPIs for the new time range | `start_time`, `end_time`, `filters` |
| Click refresh | RefreshCurrentView | POST | `/views/current/refresh` | Refresh data based on current view configuration | `view_id`, `force`, `last_query_token` |
| Save current view | SaveView | POST | `/views` | Save filters, charts, and column configuration | `name`, `tab`, `filters`, `layout`, `visibility` |
| Export current result | ExportView | POST | `/export` | Export CSV/PNG/Markdown report | `view_id`, `format`, `scope`, `time_range` |

### 12.4.3 Tab Switching APIs

| Interaction | API Name | Method | Path | Function | Parameters |
|---|---|---|---|---|---|
| Switch to Overview | QueryOverviewSummary | POST | `/overview/summary` | Get Overview KPIs, matrix, and TopN summary | `time_range`, `filters` |
| Switch to Resources | QueryResourceInventory | POST | `/resources/query` | Get resource table and inventory summary | `time_range`, `filters`, `page`, `sort` |
| Switch to Jobs | QueryJobs | POST | `/jobs/query` | Get job list and job summary | `time_range`, `filters`, `page`, `sort` |
| Switch to Trends | InitMetricExplorer | GET | `/trends/config` | Get selectable metrics, aggregations, and group-by configuration | `tab=trends`, `vendor`, `model` |
| Switch to Alerts | SearchAlerts | POST | `/alerts/search` | Get alert list | `time_range`, `severity[]`, `status[]`, `filters` |
| Switch to Cost | QueryCostCapacitySummary | POST | `/cost-capacity/summary` | Get cost, card-hours, queue, and watermark data | `time_range`, `filters`, `cost_mode` |
| Switch to Settings | GetSettings | GET | `/settings` | Get metrics, thresholds, and collection Profile configuration | `workspace_id` |

### 12.4.4 Filter APIs

| Interaction | API Name | Method | Path | Function | Parameters |
|---|---|---|---|---|---|
| Open Region dropdown | ListRegions | GET | `/meta/regions` | Get Region options and status | `q`, `workspace_id` |
| Open Cluster dropdown | ListClusters | GET | `/meta/clusters` | Get Cluster options | `region_ids[]`, `q` |
| Open accelerator model dropdown | ListAcceleratorTypes | GET | `/meta/accelerator-types` | Get accelerator model options | `region_ids[]`, `vendor[]` |
| Open Job dropdown | SearchJobs | GET | `/meta/jobs/search` | Search Job | `q`, `time_range`, `tenant_ids[]` |
| Open tenant dropdown | ListTenants | GET | `/meta/tenants` | Get tenants | `q`, `workspace_id` |
| Add dimension filter | QueryCurrentTabData | POST | `/query/current-tab` | Refresh current tab with new filters | `tab`, `filters`, `time_range`, `layout` |
| Add metric value filter | ValidateMetricFilter | POST | `/filters/metric/validate` | Validate expression | `expression`, `metric_id` |
| Apply metric value filter | QueryCurrentTabData | POST | `/query/current-tab` | Backend executes metric value filter | `metric_filters[]`, `filters`, `time_range` |
| Reset filters | QueryCurrentTabData | POST | `/query/current-tab` | Refresh with default filters | `tab`, `default_filters=true` |
| Save filter preset | SaveFilterPreset | POST | `/filters/presets` | Save frequently used filters | `name`, `filters`, `metric_filters` |

### 12.4.5 Overview Card APIs

| Interaction | API Name | Method | Path | Function | Parameters |
|---|---|---|---|---|---|
| Load 4 main KPIs | QueryOverviewSummary | POST | `/overview/summary` | Return health, utilization, cost, and alert summary | `time_range`, `filters`, `compare_mode` |
| Load Region × model matrix | QueryRegionModelMatrix | POST | `/overview/region-model-matrix` | Return health rate, utilization, and alert count for each cell | `time_range`, `filters`, `metrics[]` |
| Click matrix cell | QueryResourceInventory | POST | `/resources/query` | Enter Resources with filters applied | `region_id`, `accelerator_model`, `time_range` |
| Load abnormal TopN | QueryTopN | POST | `/query/topn` | Return abnormal accelerator/job/node TopN | `metric_id`, `rank_by`, `n`, `filters` |
| Switch TopN tab | QueryTopN | POST | `/query/topn` | Refresh TopN by selected type | `topn_type`, `time_range`, `filters` |
| Click TopN row | GetResourceDetail / GetJobDetail | GET | `/resources/{id}` or `/jobs/{id}` | Open Detail Drawer | `id`, `time_range` |
| Load event timeline | QueryEventTimeline | POST | `/events/timeline` | Return alerts, Kubernetes, checkpoint, and hardware events | `time_range`, `filters`, `event_types[]` |

### 12.4.6 Resources APIs

| Interaction | API Name | Method | Path | Function | Parameters |
|---|---|---|---|---|---|
| Load resource table | QueryResourceInventory | POST | `/resources/query` | Paginated query for Region/Node/Accelerator | `filters`, `columns[]`, `page`, `page_size`, `sort` |
| Switch hierarchy view | QueryResourceInventory | POST | `/resources/query` | Aggregate by Region/Cluster/Node/Accelerator | `view_level`, `group_by[]`, `filters` |
| Sort table | QueryResourceInventory | POST | `/resources/query` | Server-side sorting | `sort_by`, `sort_order` |
| Customize columns | SaveTableColumns | POST | `/settings/table-columns` | Save column configuration | `tab`, `columns[]` |
| Open single-accelerator Drawer | GetAcceleratorDetail | GET | `/resources/accelerators/{accelerator_id}` | Return accelerator identity, state, and capabilities | `accelerator_id` |
| Fetch single-accelerator trends | QueryMetricRange | POST | `/query/range` | Return multi-metric time series for one accelerator | `metric_ids[]`, `filters.accelerator_id`, `time_range`, `resolution` |
| Fetch single-accelerator events | QueryEventTimeline | POST | `/events/timeline` | Return accelerator events | `resource_type=accelerator`, `resource_id`, `time_range` |
| Mark maintenance | MarkResourceMaintenance | POST | `/resources/maintenance` | Put resource into maintenance state | `resource_type`, `resource_id`, `reason`, `until` |
| Create resource alert rule | CreateAlertRule | POST | `/alerts/rules` | Create a rule based on current resource | `metric_id`, `resource_selector`, `condition`, `severity` |

### 12.4.7 Jobs APIs

| Interaction | API Name | Method | Path | Function | Parameters |
|---|---|---|---|---|---|
| Load Job list | QueryJobs | POST | `/jobs/query` | Query job list | `filters`, `metric_filters`, `page`, `sort` |
| Search Job | SearchJobs | GET | `/meta/jobs/search` | Search by name/ID/user | `q`, `time_range`, `tenant_ids[]` |
| Open Job details | GetJobDetail | GET | `/jobs/{job_id}` | Return job metadata, resource bindings, status | `job_id` |
| Get Job summary | GetJobSummary | GET | `/jobs/{job_id}/summary` | Return throughput, Step, MFU, Goodput, cost | `job_id`, `start_time`, `end_time` |
| Get Step breakdown | QueryJobStepBreakdown | POST | `/jobs/{job_id}/step-breakdown` | Return forward/backward/communication/IO breakdown | `job_id`, `time_range`, `aggregation` |
| Get single-card skew matrix | QueryJobAcceleratorSkew | POST | `/jobs/{job_id}/accelerator-skew` | Return relative deviation for each accelerator | `job_id`, `metric_ids[]`, `time_range` |
| Get communication analysis | QueryJobCommunication | POST | `/jobs/{job_id}/communication` | Return NCCL/collective communication metrics | `job_id`, `collective_types[]`, `time_range` |
| Get IO analysis | QueryJobIO | POST | `/jobs/{job_id}/io` | Return DataLoader/storage/copy metrics | `job_id`, `time_range` |
| Get training anomalies | QueryTrainingAnomalies | POST | `/jobs/{job_id}/anomalies` | Return loss spike, NaN/Inf, etc. | `job_id`, `time_range`, `types[]` |
| Start short profiler | StartProfilerSession | POST | `/jobs/{job_id}/profiler/sessions` | Enable expert sampling for a specified job | `job_id`, `duration_seconds`, `profile_items[]` |
| Get profiler result | GetProfilerSession | GET | `/jobs/{job_id}/profiler/sessions/{session_id}` | Return operator TopN and trace status | `job_id`, `session_id` |

### 12.4.8 Trends / Metric Explorer APIs

| Interaction | API Name | Method | Path | Function | Parameters |
|---|---|---|---|---|---|
| Open metric selector | ListMetricDictionary | GET | `/metrics/dictionary` | Metric list and definitions | `layer`, `priority`, `scope`, `vendor` |
| Query single-metric trend | QueryMetricRange | POST | `/query/range` | Return time series | `metric_id`, `filters`, `time_range`, `resolution` |
| Query multi-metric trend | QueryMultiMetricRange | POST | `/query/range/multi` | Return multi-metric, multi-series data | `metric_ids[]`, `filters`, `group_by[]` |
| Query rollup trend | QueryRollupRange | POST | `/query/rollup-range` | Return trend aggregated by group by | `metric_id`, `aggregation`, `group_by[]`, `filters` |
| Query distribution | QueryDistribution | POST | `/query/distribution` | Return histogram/box plot | `metric_id`, `bucket`, `filters`, `time_range` |
| Query TopN trend | QueryTopNOverTime | POST | `/query/topn-over-time` | Return ranking changes over time | `metric_id`, `n`, `group_by`, `time_range` |
| Add baseline comparison | QueryCompare | POST | `/query/compare` | Same-time yesterday / previous period / peer baseline | `metric_id`, `compare_mode`, `baseline_selector` |
| Chart brush | QueryDrilldownByTimeRange | POST | `/query/drilldown` | Query events and details for selected time range | `time_range`, `filters`, `metric_context` |

### 12.4.9 Alerts APIs

| Interaction | API Name | Method | Path | Function | Parameters |
|---|---|---|---|---|---|
| Load alert list | SearchAlerts | POST | `/alerts/search` | Paginated alert query | `time_range`, `severity[]`, `status[]`, `filters`, `page` |
| Open alert detail | GetAlertDetail | GET | `/alerts/{alert_id}` | Return alert details, rule, related events | `alert_id` |
| Acknowledge alert | AckAlert | PATCH | `/alerts/{alert_id}` | Change status to acknowledged | `status`, `comment` |
| Silence alert | SilenceAlert | POST | `/alerts/silences` | Create silence rule | `matcher`, `start_time`, `end_time`, `reason` |
| Resolve alert | ResolveAlert | PATCH | `/alerts/{alert_id}` | Manual resolution | `status=resolved`, `comment` |
| Create rule | CreateAlertRule | POST | `/alerts/rules` | Create alert rule | `name`, `metric_id`, `condition`, `filters`, `severity` |
| Update rule | UpdateAlertRule | PATCH | `/alerts/rules/{rule_id}` | Modify rule | `condition`, `severity`, `enabled` |
| Test rule | TestAlertRule | POST | `/alerts/rules/test` | Return historical matches | `condition`, `filters`, `time_range` |

### 12.4.10 Cost & Capacity APIs

| Interaction | API Name | Method | Path | Function | Parameters |
|---|---|---|---|---|---|
| Load cost summary | QueryCostCapacitySummary | POST | `/cost-capacity/summary` | Card-hours, cost, Goodput, queue | `time_range`, `filters`, `cost_model` |
| Cost grouping | QueryCostBreakdown | POST | `/cost-capacity/breakdown` | Group by Region/tenant/job/model | `group_by[]`, `metrics[]`, `filters` |
| Inefficiency TopN | QueryWasteTopN | POST | `/cost-capacity/waste-topn` | Low-utilization card-hours/job/tenant TopN | `n`, `rank_by`, `filters` |
| Queue analysis | QueryQueueMetrics | POST | `/cost-capacity/queue` | Queue time, queue depth, scheduling failures | `queue_names[]`, `time_range`, `filters` |
| Resource fragmentation | QueryFragmentation | POST | `/cost-capacity/fragmentation` | Return fragmentation ratio and unschedulable resources | `region_ids[]`, `accelerator_models[]` |
| Capacity forecast | QueryCapacityForecast | POST | `/cost-capacity/forecast` | 7d/30d forecast | `metric_id`, `horizon`, `filters` |

### 12.4.11 Metric Explanation and Context APIs

| Interaction | API Name | Method | Path | Function | Parameters |
|---|---|---|---|---|---|
| Hover metric name | GetMetricDefinition | GET | `/metrics/{metric_id}` | Return definition, unit, formula, and differences from similar metrics | `metric_id`, `vendor`, `model` |
| Click “Why anomalous?” | ExplainMetricAnomaly | POST | `/explain/anomaly` | Return candidate anomaly causes | `metric_id`, `resource_ref`, `time_range`, `context_metrics[]` |
| Open “Differences from similar metrics” | GetMetricRelations | GET | `/metrics/{metric_id}/relations` | Return related metrics and differences | `metric_id` |
| Open collection status | GetMetricSourceStatus | GET | `/metrics/{metric_id}/source-status` | Return exporter / adapter / stale status | `metric_id`, `filters` |

---

## 12.5 API Request Examples

### 12.5.1 Query Rollup Trend

```http
POST /api/v1/monitor/query/rollup-range
Content-Type: application/json
```

```json
{
  "metric_id": "accelerator.utilization.compute.pct",
  "time_range": {
    "start_time": "2026-06-09T00:00:00Z",
    "end_time": "2026-06-09T06:00:00Z"
  },
  "resolution": "1m",
  "filters": {
    "region_ids": ["cn-hangzhou", "cn-wulanchabu"],
    "accelerator_models": ["H200", "ZHENWU_810E"],
    "health_status": ["healthy", "warning"]
  },
  "metric_filters": [
    {
      "metric_id": "accelerator.memory.used.pct",
      "operator": ">",
      "value": 70,
      "duration": "10m"
    }
  ],
  "group_by": ["region_id", "accelerator_model"],
  "aggregation": "weighted_avg"
}
```

### 12.5.2 Query TopN Low-Utilization Accelerators

```http
POST /api/v1/monitor/query/topn
```

```json
{
  "rank_by": "low_utilization_allocated_minutes",
  "n": 20,
  "time_range": {
    "start_time": "2026-06-09T00:00:00Z",
    "end_time": "2026-06-09T06:00:00Z"
  },
  "filters": {
    "allocated": true,
    "region_ids": ["cn-hangzhou"],
    "accelerator_models": ["H200"]
  },
  "condition": {
    "metric_id": "accelerator.utilization.compute.pct",
    "operator": "<",
    "value": 20,
    "duration": "15m"
  },
  "return_fields": [
    "accelerator_id",
    "node_id",
    "job_id",
    "tenant_id",
    "avg_utilization",
    "allocated_minutes",
    "estimated_waste_cost"
  ]
}
```

### 12.5.3 Open Single-Accelerator Details

```http
GET /api/v1/monitor/resources/accelerators/acc-cn-hz-node01-3?include=current_job,capability,health,source_status
```

Core response fields:

```json
{
  "accelerator_id": "acc-cn-hz-node01-3",
  "vendor": "nvidia",
  "model": "H200",
  "region_id": "cn-hangzhou",
  "node_id": "node01",
  "device_index": 3,
  "health_status": "warning",
  "current_job": {
    "job_id": "job-llm-20260609-001",
    "job_name": "qwen-pretrain-stage3"
  },
  "capability": {
    "metrics_supported": [
      "accelerator.utilization.compute.pct",
      "accelerator.memory.used.pct",
      "accelerator.power.watt",
      "accelerator.temperature.celsius",
      "accelerator.errors.xid.count"
    ],
    "metrics_missing": []
  },
  "source_status": {
    "dcgm_exporter": "healthy",
    "kubelet": "healthy",
    "training_hook": "healthy"
  }
}
```

---

## 13. Permissions and Multi-Tenancy

### 13.1 Permission Model

| Permission | Can See | Cannot See |
|---|---|---|
| Platform Admin | All Regions, resources, cost, alerts, configuration | None |
| SRE | All resource health, alerts, and job technical metrics | Cost amounts may be hidden; only cost index shown |
| Tenant Admin | Jobs, card-hours, cost, and efficiency for their own tenant | Other tenants’ job names and user information |
| User | Jobs they submitted and associated resources | Details of other users’ jobs |
| Viewer | Aggregated metrics | Sensitive single-accelerator information, cost, user information |

### 13.2 Desensitization Rules

| Data | Rule |
|---|---|
| Job name | For unauthorized tenants, display hash or alias. |
| Username | For unauthorized users, display user hash. |
| Cost amount | Without FinOps permission, show normalized cost index. |
| Node hostname | Across tenants, display node alias. |
| Dataset / Bucket | Show only hash, not raw path. |

---

## 14. Data Quality and Abnormal States

### 14.1 Data States

| State | Description | UI Representation |
|---|---|---|
| complete | Data is complete for all Regions | Normal display |
| partial | Some Regions or data sources are missing | `Partial` badge in card top-right |
| stale | Data exceeds freshness SLA | Gray overlay + stale time |
| empty | No data | Empty state, guiding user to modify filters or check collection |
| unsupported | Current accelerator model does not support this metric | Display `Not supported by this adapter` |

### 14.2 Freshness SLA

| Metric Priority | Expected Freshness | Timeout Representation |
|---|---:|---|
| P0 | <= 5s | Red `stale`, alert |
| P1 | <= 30s | Orange `stale` |
| P2 | <= 5min | Gray hint |
| P3 | <= 1h | Settings-page hint only |

---

## 15. Alerting Strategy

### 15.1 Threshold Types

| Type | Example | Use Case |
|---|---|---|
| Fixed threshold | Temperature > 85°C | Hardware health |
| Event-triggered | Xid errors increase > 0 | Hardware errors |
| Baseline deviation | Step time > historical same-job P95 × 1.2 | Performance degradation |
| YoY/period-over-period | Tokens/s decreases by 20% versus same time yesterday | Operational trend |
| Composite condition | High memory + low compute + high data wait | Attribution alert |
| SLO | Queue P95 > 30min | Platform service quality |

### 15.2 Alert Noise Reduction

| Mechanism | Description |
|---|---|
| Deduplication | Aggregate by same resource + rule. |
| Inhibition | When a single accelerator is offline, suppress derived alerts such as low utilization and missing temperature for the same card. |
| Merging | Multiple-card anomalies on the same Node are merged into a node-level incident. |
| Maintenance window | After marking maintenance, silence non-critical alerts. |
| Auto-resolution | Resolve after the metric recovers and stays normal for a period. |
| Recurrence detection | If the same resource and rule recur within 24h, mark as `recurring`. |

---

## 16. Performance, Capacity, and Engineering Constraints

### 16.1 Time-Series Storage Retention Strategy

| Data | Resolution | Retention | Use |
|---|---:|---:|---|
| Raw P0 | 1s~5s | 6h~24h | Real-time troubleshooting |
| Standard | 15s | 7d | Daily trends |
| Rollup 1m | 1m | 90d | Operational analysis |
| Rollup 5m | 5m | 180d | Capacity planning |
| Rollup 1h | 1h | 2y | Cost and trend reports |
| Events | event | 2y | Alerts, audit, postmortem |

### 16.2 Cardinality Control

| Risk | Control Method |
|---|---|
| High cardinality from job names and Pod names | Only IDs/hashes are used as labels; names are stored in metadata. |
| High cardinality from profiler operator names | Not stored in core TSDB; stored in profile store. |
| Unlimited user-defined tags | Allowlist, at most 10 indexable tags. |
| Slow Region aggregation queries | Precompute common rollups and TopN. |
| Too many metrics affecting UI | L0/L1/L2 layering; Expert Mode disabled by default. |

### 16.3 Query Performance Targets

| Query Type | P95 Target |
|---|---:|
| Overview first screen | < 1.5s |
| Resource table pagination | < 1.2s |
| Single-accelerator details | < 800ms |
| 6h trend | < 1.5s |
| 7d rollup trend | < 2.5s |
| TopN | < 2s |
| Job Step breakdown | < 2.5s |

---

## 17. Product Iteration Roadmap

### 17.1 MVP: 4–6 Weeks

| Scope | Features |
|---|---|
| Data | NVIDIA DCGM, Kubernetes, basic Job Hook, basic PPU Adapter |
| Pages | Overview, Resources, Alerts |
| Metrics | L0 + partial L1: health, utilization, memory, temperature, power, errors, Kubernetes state |
| Filters | Region, Cluster, accelerator model, Node, Job, health status, metric threshold |
| Aggregation | avg/max/min/sum/topN/basic trend |
| APIs | bootstrap, meta, summary, resource query, range query, alert search |

### 17.2 V1: 8–10 Weeks

| Scope | Features |
|---|---|
| Data | NCCL, DataLoader, Checkpoint, Cost, Queue |
| Pages | Jobs, Trends, Cost & Capacity |
| Metrics | Complete L1 |
| Interactions | Trend explorer, Brush, Compare, complete Detail Drawer |
| Alerts | Composite rules, silence, recurrence detection, rule testing |

### 17.3 V2: 12+ Weeks

| Scope | Features |
|---|---|
| Data | Profiler/eBPF/expert metrics, more chip adapters |
| Pages | Expert Mode, Topology, Capacity Forecast |
| Intelligent analysis | Anomaly attribution, automatic filter recommendations, similar-job comparison |
| Operations | SLO, budget, scaling recommendations, automated maintenance flow |

---

## 18. Multi-Round Review and Optimization Conclusions

### 18.1 Richness vs Simplicity

| Review Point | Risk | Decision |
|---|---|---|
| Metric system is large | The homepage becomes packed with metrics and users cannot identify priorities | Only 12 L0 metrics are shown on the homepage; the rest go to drill-down pages and Expert Mode. |
| User roles differ greatly | One page cannot satisfy everyone | Use SPA multi-tab design while keeping a unified filter bar and unified detail Drawer. |
| Expert metrics are valuable | Collection overhead is high and UI complexity increases | Expert Profile is enabled by job/time window and not enabled globally by default. |

### 18.2 Logic and Hierarchy

| Review Point | Decision |
|---|---|
| Relationship between pages | Overview is the entry; Resources explains hardware and system; Jobs explains training efficiency; Trends compares; Alerts closes the loop; Cost handles operations. |
| Metric progression | Health → Utilization → Bottleneck → Cost → Trend → Action. |
| Card relationship | KPI Cards give conclusions, matrix locates dimensions, TopN locates objects, Drawer provides context. |

### 18.3 Interaction Comprehensibility

| Review Point | Decision |
|---|---|
| Metric definitions | All core metrics show definition, unit, source, and differences from similar metrics on hover or click. |
| Filter complexity | Provide natural-language summaries and common presets. |
| Multi-model semantics | Metric Tooltip shows support status and adapter semantics for the current accelerator model. |
| Trend charts are hard to interpret | Overlay events, job phases, and alerts to avoid reading curves in isolation. |

---

## 19. Acceptance Criteria

### 19.1 Product Acceptance

| Acceptance Item | Standard |
|---|---|
| Multi-Region | Any metric supports filtering, group by, rollup, and trend by Region. |
| Multi-model | H200, RTX PRO 5000, and PPU can at least be displayed in the same resource table and can show their supported/unsupported metrics. |
| Dimension filters | Region, Cluster, Node, model, Job, tenant, user, health status, framework, and parallel strategy can be combined. |
| Metric value filters | Supports `>`, `<`, `between`, `increase`, `rate`, `baseline deviation`, `topN`. |
| Aggregation analysis | Supports sum, avg, weighted avg, max, min, p95/p99, TopN, distribution. |
| Trend analysis | Supports single-accelerator trends and trends aggregated by any dimension. |
| UI | Complies with Notion-style tokens, SPA, multi-tab, multi-card, Tooltip, Drawer. |
| API | Every backend interaction has a clear API, method, and parameters. |
| Data quality | partial/stale/unsupported states are clearly expressed in the UI. |

### 19.2 Technical Acceptance

| Acceptance Item | Standard |
|---|---|
| First-screen performance | P95 < 1.5s. |
| Query performance | 6h trend P95 < 1.5s; 7d rollup P95 < 2.5s. |
| Data freshness | P0 <= 5s, P1 <= 30s. |
| Permission isolation | Tenants cannot view unauthorized jobs, users, or cost. |
| Metric governance | All metrics must be registered in the metric dictionary; unregistered metrics are not displayed. |
| Adapter capability | Each accelerator model returns supported/missing/estimated metric lists. |

---

## 20. Appendix: Core API Summary

| API | Method | Path |
|---|---|---|
| GetBootstrap | GET | `/api/v1/monitor/bootstrap` |
| ListRegions | GET | `/api/v1/monitor/meta/regions` |
| ListClusters | GET | `/api/v1/monitor/meta/clusters` |
| ListAcceleratorTypes | GET | `/api/v1/monitor/meta/accelerator-types` |
| ListMetricDictionary | GET | `/api/v1/monitor/metrics/dictionary` |
| QueryOverviewSummary | POST | `/api/v1/monitor/overview/summary` |
| QueryRegionModelMatrix | POST | `/api/v1/monitor/overview/region-model-matrix` |
| QueryCurrentTabData | POST | `/api/v1/monitor/query/current-tab` |
| QueryMetricRange | POST | `/api/v1/monitor/query/range` |
| QueryRollupRange | POST | `/api/v1/monitor/query/rollup-range` |
| QueryTopN | POST | `/api/v1/monitor/query/topn` |
| QueryDistribution | POST | `/api/v1/monitor/query/distribution` |
| QueryCompare | POST | `/api/v1/monitor/query/compare` |
| QueryResourceInventory | POST | `/api/v1/monitor/resources/query` |
| GetAcceleratorDetail | GET | `/api/v1/monitor/resources/accelerators/{accelerator_id}` |
| QueryJobs | POST | `/api/v1/monitor/jobs/query` |
| GetJobDetail | GET | `/api/v1/monitor/jobs/{job_id}` |
| QueryJobStepBreakdown | POST | `/api/v1/monitor/jobs/{job_id}/step-breakdown` |
| QueryJobAcceleratorSkew | POST | `/api/v1/monitor/jobs/{job_id}/accelerator-skew` |
| SearchAlerts | POST | `/api/v1/monitor/alerts/search` |
| CreateAlertRule | POST | `/api/v1/monitor/alerts/rules` |
| QueryCostCapacitySummary | POST | `/api/v1/monitor/cost-capacity/summary` |
| SaveView | POST | `/api/v1/monitor/views` |
| ExportView | POST | `/api/v1/monitor/export` |

---

## 21. Appendix: Reference Mapping

| Reference | Role in This Design |
|---|---|
| AI Compute Monitoring Platform Metric Classification System | Metric layers, collection granularity, frequency, aggregation, alert strategy, and P0–P3 priorities. |
| Notion design analysis | UI colors, typography, border radius, cards, tabs, buttons, responsive behavior, and visual constraints. |
| NVIDIA DCGM / DCGM Exporter | NVIDIA GPU telemetry collection and Prometheus exposure method. |
| NVIDIA DCGM Field IDs | Raw-field mapping for metric dictionary. |
| Kubernetes Resource Metrics Pipeline | Source for Node/Pod/Container resource metrics. |
| Prometheus Query Functions | Design basis for time-window aggregation, TopN, rate/increase queries. |
| Thanos / Mimir / OpenTelemetry | Unified multi-Region metric querying and unified data model. |
| NVIDIA H200 / RTX PRO 5000 official specs | Accelerator capability metadata. |
| Alibaba Cloud Zhenwu PPU / PAI-PPU documentation | PPU adaptation, PAI/ACS usage, and accelerator model metadata. |
| NCCL / PyTorch Profiler | Distributed communication and expert analysis for training performance. |
