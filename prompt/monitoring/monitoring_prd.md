# 大模型训练平台算力资源监控模块产品设计文档 v1.0

> 角色定位：AI Infra 平台产品 / SRE / 训练性能分析 / 多云算力运营  
> 目标形态：单页面 SPA、多 Tab、多 Card、Notion 风格监控工作台  
> 覆盖范围：多 Region、多集群、多类型 AI 加速卡，含 NVIDIA H200、NVIDIA RTX PRO 5000 Blackwell、阿里云真武 PPU、以及后续可扩展的 NPU/GPU/ASIC 适配  
> 设计原则：指标足够丰富，但首页克制；链路清晰，先整体后下钻；每个指标都能被解释、对比、过滤、聚合和追踪

---

## 0. 设计文档整体说明

1. **先建立产品问题闭环**：用户不是来“看一堆指标”的，而是要回答：算力是否健康、资源是否浪费、训练为何变慢、哪个 Region/卡型/任务拖后腿、是否需要迁移或扩容。
2. **指标分层而不是平铺**：将 `monitoring_metrics.md` 的五层指标体系压缩成三级展示策略：
   - L0 首页核心指标：值班 / 管理者 / 资源运营需要快速判断。
   - L1 标准分析指标：SRE 和训练工程师日常排障使用。
   - L2 专家诊断指标：性能优化、芯片适配、框架调优时再打开。
3. **多 Region、多卡型是底层数据模型能力，而不是几个筛选框**：统一抽象 `accelerator`，通过 vendor adapter 接入 DCGM/NVML、PPU SDK、K8s、NCCL、Profiler、eBPF、网络和存储 exporter。
4. **UI 按 Notion 设计语言落地到像素级**：提供页面结构、尺寸、颜色、字体、Card、Tab、Tooltip、Drawer、表格、趋势图和响应式规则。
5. **所有触发后端请求的交互均绑定 API**：包括页面加载、Tab 切换、过滤、聚合、TopN、趋势刷新、下钻、指标说明、告警确认、保存视图、导出等。
6. **增加设计审查结论**：用 AI Infra SRE、GPU/NCCL 性能专家、平台产品专家、前端交互专家四个视角反复审查，避免“指标贪多”和“UI 看似漂亮但不可用”。

---

## 1. 产品定位与边界

### 1.1 产品一句话

面向大模型训练平台的 **跨 Region 异构算力资源监控与分析工作台**，帮助平台团队用一个页面完成算力健康巡检、资源利用率分析、训练瓶颈定位、单卡异常下钻、汇总趋势对比和告警闭环。

### 1.2 核心用户

| 用户角色 | 典型问题 | 最高频动作 | 需要的默认视图 |
|---|---|---|---|
| 平台 SRE / 值班同学 | 现在是否有掉卡、过热、Xid、ECC、网络异常？ | 看全局健康、Top 异常、告警确认、下钻节点 | Overview + Alerts |
| 训练工程师 | 我的 Job 为什么变慢？是计算、通信、IO 还是显存？ | 搜索 Job、看 Step time 拆解、看单卡/Pod 趋势 | Job Analysis |
| 资源运营 / FinOps | 哪些卡闲置？哪些团队资源使用效率差？ | 按租户、Region、卡型汇总，找低利用率 TopN | Overview + Cost & Capacity |
| 平台管理员 | 哪些 Region/卡型要扩容、下线或迁移？ | 跨 Region/卡型趋势比较、容量预测 | Trends + Resources |
| 芯片/框架适配工程师 | 新卡型或 PPU 指标是否完整？性能是否符合预期？ | 看指标字典、驱动/SDK 版本、专家指标 | Resources + Settings |

### 1.3 不做什么

本模块不是完整 APM、不是训练实验管理平台、不是成本账单平台、不是通用 BI。它只做一件事：**围绕训练算力，把硬件健康、资源利用、训练效率和运营成本串成可排障、可聚合、可下钻的监控体验**。

---

## 2. 专业资料与领域依据

### 2.1 内部上传文档采用方式

| 文档 | 采用方式 |
|---|---|
| `monitoring_metrics.md` | 作为指标体系主来源，保留其五层架构：硬件、系统运行时、训练框架、任务模型、业务成本；同时按 P0/P1/P2/P3 对展示优先级做产品裁剪。 |
| `DESIGN.md` | 作为 UI 视觉和组件规范来源，采用 Notion 风格的颜色、字体、Card、Tab、按钮、间距、圆角和响应式规则。 |

### 2.2 外部专业资料采用方式

| 来源类型 | 采用到产品设计中的内容 |
|---|---|
| NVIDIA DCGM / DCGM Exporter 官方文档 | NVIDIA GPU 监控采集方案，DCGM Exporter 通过 `/metrics` 暴露给 Prometheus；指标字典中保留 DCGM field id 映射。 |
| Kubernetes Metrics Server / kubelet resource metrics 官方文档 | 作为 Pod / Node / Container CPU、内存、资源请求和调度相关指标的数据来源之一。 |
| Prometheus 官方查询函数 | 作为区间聚合、avg/sum/count over time、TopN、rate/increase、histogram quantile 等查询能力的设计基础。 |
| Thanos / Mimir / OpenTelemetry 官方文档 | 作为多 Region、多集群指标统一查询、长期存储、多租户和统一指标数据模型的架构参考。 |
| NVIDIA H200 / RTX PRO 5000 官方规格 | 作为卡型能力元数据，不硬编码指标含义，但用于峰值算力、显存容量、功耗上限、带宽等归一化计算。 |
| 阿里云真武 PPU / PAI-PPU 文档 | 作为 PPU 适配依据，产品层抽象为 accelerator，不将 GPU 专属概念强行套到 PPU。 |
| NCCL / PyTorch Profiler 官方文档 | 作为分布式通信、Step 性能拆解、算子耗时、Profiler 专家模式的来源。 |

### 2.3 专家审查视角

无法真实向外部人类专家发起实时咨询，因此本设计将“专家审查”固化为四类评审视角，并在每个核心章节给出审查结论：

| 专家视角 | 审查重点 | 本版落实 |
|---|---|---|
| AI Infra SRE | 故障发现是否快、指标是否可告警、是否能定位到节点/卡/Pod/Job | 首页只放 P0/P1；所有异常卡、节点、Job 都可下钻到事件时间线。 |
| GPU/NCCL 性能专家 | 是否区分 GPU 利用率、SM/Tensor 利用率、MFU、通信等待、数据等待 | 指标字典内置“相近指标差异”；Job 页面按计算/通信/IO/等待拆解。 |
| 平台产品专家 | 是否避免堆砌指标；用户是否按自然路径排障 | 信息架构采用“总览 → 汇总比较 → TopN → 下钻单卡/Job → 告警/修复”的递进路径。 |
| 前端交互专家 | 是否一眼能看懂，过滤和 Tooltip 是否顺手 | 采用 Notion 式轻量 Card、pill tab、右侧 Drawer、指标解释 Popover 和保存视图。 |

---

## 3. 产品问题闭环

### 3.1 六个必须回答的问题

| 编号 | 用户问题 | 首屏答案 | 下钻答案 |
|---|---|---|---|
| Q1 | 当前整体算力健康吗？ | 健康卡占比、异常卡数、P0 告警数、不可用卡数 | 异常卡列表、节点事件、Xid/ECC/掉卡/温度时间线 |
| Q2 | 资源是否被有效使用？ | 已分配卡数、活跃训练卡数、平均利用率、低利用率卡 TopN | 按 Region/卡型/租户/Job 维度拆分低利用率原因 |
| Q3 | 哪个 Region 或卡型拖后腿？ | Region × 卡型矩阵、利用率/故障率/排队时间 | 进入 Region 或卡型详情，看趋势和 TopN |
| Q4 | 某个 Job 为什么慢？ | Step time、Tokens/s、MFU、等待通信/数据比例 | 单卡趋势、通信算子、DataLoader、Checkpoint、Pod 事件 |
| Q5 | 是否存在资源浪费或成本异常？ | 空置卡时、低利用率卡时、每百万 Token 成本 | 租户/用户/Job 成本排名、Goodput 趋势 |
| Q6 | 是否需要迁移、扩容或限流？ | 容量水位、队列深度、SLO 达成率 | 历史趋势、预测、资源碎片、调度失败原因 |

### 3.2 主要用户路径

```text
打开 Overview
  ↓
看健康与利用率摘要
  ↓
按 Region / 卡型 / 租户 / Job 加过滤
  ↓
查看 Region × 卡型矩阵与 TopN 异常
  ↓
点击某个异常卡、节点或 Job
  ↓
进入资源详情 / Job 分析 Drawer
  ↓
查看时间线、趋势、事件、相近指标解释
  ↓
确认告警、保存视图、导出分析或跳转修复动作
```

---

## 4. 信息架构

### 4.1 SPA 顶层 Tab

| Tab | 中文名 | 主要服务对象 | 主要回答 |
|---|---|---|---|
| Overview | 总览 | SRE / 资源运营 | 当前健康吗、哪里异常、哪里浪费？ |
| Resources | 算力资源 | SRE / 芯片适配 | 单卡、节点、Region、卡型明细如何？ |
| Jobs | 训练任务 | 训练工程师 | 任务慢在哪里，单卡是否拖后腿？ |
| Trends | 趋势分析 | 平台管理员 / 资源运营 | 不同 Region/卡型/租户的时间趋势如何？ |
| Alerts | 告警事件 | SRE | 哪些告警需要处理，历史是否复发？ |
| Cost & Capacity | 成本与容量 | FinOps / 管理者 | 卡时、空置成本、队列和容量水位如何？ |
| Settings | 指标与配置 | 平台管理员 | 指标字典、阈值、采集 Profile、视图模板如何配置？ |

### 4.2 页面层次

```text
Global Shell
├─ Top Bar：产品名、全局搜索、时间范围、刷新、导出、用户视图
├─ Left Rail：Region/Workspace 快捷入口、收藏视图、最近访问
├─ Page Header：当前 Tab 标题、健康摘要、全局过滤器
├─ Tab Content
│  ├─ Summary Cards
│  ├─ Matrix / Chart Cards
│  ├─ TopN / Table Cards
│  └─ Detail Drawer / Modal
└─ Toast / Alert Center
```

---

## 5. 统一数据模型

### 5.1 核心对象

| 对象 | 说明 | 关键字段 |
|---|---|---|
| Region | 地域，支持云厂商 Region、自建机房 Region | `region_id`, `region_name`, `cloud_provider`, `timezone`, `status` |
| Cluster | 单 Region 内的集群 | `cluster_id`, `region_id`, `k8s_version`, `network_type`, `storage_type` |
| Node | 物理机或裸金属实例 | `node_id`, `cluster_id`, `rack_id`, `hostname`, `instance_type`, `os`, `kernel`, `driver_version` |
| Accelerator | 单张 AI 加速卡的统一抽象 | `accelerator_id`, `node_id`, `vendor`, `model`, `device_index`, `uuid`, `memory_total_gb`, `power_limit_w`, `health_status` |
| AcceleratorType | 卡型元数据 | `vendor`, `model`, `architecture`, `memory_type`, `memory_total_gb`, `peak_flops`, `interconnect`, `adapter_type` |
| Job | 训练任务 | `job_id`, `job_name`, `framework`, `parallel_strategy`, `tenant_id`, `user_id`, `status`, `start_time` |
| Pod / Container | K8s 运行实体 | `namespace`, `pod_name`, `container_name`, `node_id`, `job_id` |
| Metric | 指标定义 | `metric_id`, `name`, `unit`, `type`, `layer`, `priority`, `scope`, `source`, `formula`, `help_text` |
| Alert | 告警事件 | `alert_id`, `severity`, `metric_id`, `resource_ref`, `status`, `first_seen`, `last_seen` |

### 5.2 标准标签 / 维度

所有指标进入查询层后必须尽量映射到统一标签。为了控制时序基数，不允许随意把动态字符串直接打到 TSDB label。

| 维度类别 | 标准字段 | 说明 |
|---|---|---|
| 地域 | `region_id`, `zone_id`, `cluster_id` | 跨 Region 聚合的基础。 |
| 物理位置 | `rack_id`, `node_id`, `hostname` | 用于定位硬件和拓扑问题。 |
| 卡 | `accelerator_id`, `device_index`, `vendor`, `model`, `architecture` | 统一支持 GPU/PPU/NPU/ASIC。 |
| 运行实体 | `namespace`, `pod_name`, `container_name`, `process_id` | 用于从卡下钻到任务进程。 |
| 任务 | `job_id`, `job_name_hash`, `framework`, `parallel_strategy` | `job_name` 原文不进 label，避免高基数；原文在元数据表。 |
| 租户 | `tenant_id`, `workspace_id`, `user_id`, `queue_name` | 成本、配额和公平性分析。 |
| 网络 | `nic_id`, `switch_id`, `network_type`, `fabric_id` | RoCE/IB/NVLink/NVSwitch。 |
| 存储 | `storage_type`, `bucket_id_hash`, `fs_id`, `mount_id` | 数据加载与 checkpoint。 |
| 指标治理 | `metric_id`, `priority`, `collection_profile`, `source_adapter` | 指标字典和采集策略。 |

### 5.3 指标定义 Schema

```json
{
  "metric_id": "accelerator.utilization.gpu.pct",
  "display_name": "加速卡计算利用率",
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
    "definition": "采样窗口内加速卡计算单元处于 busy 的比例，用于判断卡是否被工作负载使用。",
    "difference": "不同于 MFU：MFU 衡量模型实际 FLOPs / 理论峰值，GPU 利用率高不代表模型效率高。",
    "caveat": "不同厂商对 busy 的定义不同，跨卡型对比时应优先看归一化指标和同卡型分组。"
  }
}
```

---

## 6. 多 Region 与多卡型适配设计

### 6.1 多 Region 采集与查询架构

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

### 6.2 多 Region 产品规则

| 规则 | 说明 |
|---|---|
| 默认全局视图 | 用户打开页面默认看到全部授权 Region 汇总。 |
| Region 可多选 | 任何 Tab 的过滤器都支持单选、多选、排除和收藏 Region。 |
| Region 级降级 | 某 Region 查询超时，不阻塞全局页面；卡片显示 `partial data` 状态。 |
| 时区统一 | 后端以 UTC 存储，前端按用户时区显示，同时允许切换 Region 本地时间。 |
| Region 维度始终可见 | 所有 TopN、Trend、Matrix 结果默认保留 region 标识，避免跨地域误判。 |
| 汇总使用加权规则 | 多 Region 汇总禁止简单平均；使用 `sample_count`、`card_count` 或 `allocated_card_seconds` 加权。 |

### 6.3 卡型适配矩阵

| 卡型 | 供应商 | 适配方式 | 关键能力元数据 | 指标设计注意点 |
|---|---|---|---|---|
| NVIDIA H200 | NVIDIA | DCGM Exporter + NVML + NCCL + K8s | HBM3e 141GB、内存带宽 4.8TB/s、Hopper 架构 | 支持高频 GPU/显存/功耗/温度/Xid/ECC/NVLink 指标；适合训练效率与通信分析。 |
| NVIDIA RTX PRO 5000 Blackwell | NVIDIA | DCGM/NVML 子集 + 节点 exporter | Blackwell、48GB/72GB GDDR7 ECC、内存带宽 1344GB/s、300W | 作为专业卡/工作站卡，部分数据中心能力需按实际驱动和 DCGM 支持情况灰度展示。 |
| 阿里云真武 810E / M890 PPU | Alibaba Cloud / T-Head | PPU SDK Exporter + PAI/ACS 资源元数据 + K8s | 810E 96GB、M890 144GB；片间互联 700/800GB/s；兼容主流 AI 框架和 PAI/ACS 使用场景 | 不强行展示 NVIDIA 专属字段，如 Xid、NVLink；用 `adapter_specific` 保存原生字段，再映射到通用指标。 |
| Generic Accelerator | 其他 GPU/NPU/ASIC | OpenTelemetry / Prometheus exporter adapter | 用户配置峰值算力、显存、功耗、互联类型 | 先支持 P0/P1 通用指标，专家指标按 adapter 能力扩展。 |

### 6.4 Adapter 设计

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

Adapter 必须实现：

| 方法 | 说明 |
|---|---|
| `discover()` | 发现节点、卡、驱动、SDK、拓扑和可采指标。 |
| `normalizeMetric()` | 将原始指标映射为平台标准指标。 |
| `capability()` | 返回当前卡型支持哪些指标、哪些不支持、哪些为估算。 |
| `healthCheck()` | 判断 exporter、驱动、SDK 是否工作。 |
| `explain()` | 返回指标口径说明，用于 Tooltip 和指标字典。 |

---

## 7. 指标体系产品裁剪

### 7.1 指标展示三级策略

| 层级 | 名称 | 目标 | 展示位置 | 指标数量策略 |
|---|---|---|---|---|
| L0 | 首页核心指标 | 快速判断整体状态 | Overview 首屏 Summary Cards | 12 个以内 |
| L1 | 标准分析指标 | 日常排障和容量运营 | Resources / Jobs / Trends | 每个页面 20~40 个，但分组展示 |
| L2 | 专家诊断指标 | 深度性能优化和芯片适配 | Metric Explorer / Expert Mode | 默认隐藏，按需开启 |

### 7.2 L0 首页核心指标

| 指标 | 口径 | 默认聚合 | 主要价值 | 优先级 |
|---|---|---|---|---|
| 总卡数 | 当前纳管的加速卡数量 | count | 容量基准 | P0 |
| 可用卡数 / 可用率 | `health_status=healthy` 的卡数量和占比 | count / ratio | 硬件健康 | P0 |
| 已分配卡数 / 分配率 | 被 Job/Pod 绑定的卡数 | count / ratio | 调度水位 | P0 |
| 活跃训练卡数 | 有训练负载且计算利用率超过阈值的卡数 | count | 区分“占着不用” | P0 |
| 平均计算利用率 | 按卡采样加权平均 | weighted avg | 资源使用 | P0 |
| 平均显存使用率 | 按卡显存容量加权 | weighted avg | 显存压力 | P0 |
| P0 告警数 | 当前未恢复 P0 告警 | count | 值班入口 | P0 |
| 硬件错误事件 | Xid/ECC/掉卡/PPU 原生硬件错误 | increase | 故障定位 | P0 |
| 热/功耗受限卡数 | 温度、功耗限制、热节流命中的卡 | count | 性能退化 | P1 |
| 训练吞吐量 | Tokens/s 或 Samples/s 汇总 | sum / avg | 训练产出 | P1 |
| 低利用率 TopN | 分配中但计算利用率低的卡/Job | topN | 浪费定位 | P1 |
| 空置卡时成本 | 未分配或低利用的卡时估算 | sum | 成本治理 | P1 |

### 7.3 L1 标准分析指标

#### 7.3.1 硬件与系统

| 类别 | 指标 | 默认粒度 | 默认刷新 | 展示页 |
|---|---|---:|---:|---|
| 加速卡利用 | 计算利用率、Tensor/矩阵单元利用率、显存使用率、显存带宽 | Accelerator / Job | 5s | Overview / Resources / Jobs |
| 加速卡健康 | 温度、功耗、功耗上限命中、热节流、风扇/液冷状态 | Accelerator / Node | 5s~15s | Resources / Alerts |
| 硬件错误 | Xid、ECC、掉卡、NVLink/PCIe 错误、PPU 原生 error code | Accelerator / Node | event | Resources / Alerts |
| CPU/内存 | CPU 利用率、IOWait、系统内存、NUMA 不均衡、OOM Kill | Node / Pod | 15s | Resources / Jobs |
| K8s 运行时 | Pending 时间、调度失败、重启次数、Exit Code、资源请求/限制 | Pod / Job | event~15s | Jobs / Alerts |

#### 7.3.2 网络与存储

| 类别 | 指标 | 默认粒度 | 默认刷新 | 展示页 |
|---|---|---:|---:|---|
| 机内互联 | NVLink/NVSwitch/PCIe 带宽、错误、链路状态 | Accelerator / Node | 5s | Resources / Jobs |
| 机间网络 | RoCE/IB 带宽、PFC/ECN、端口 Down、误码、P99 延迟 | NIC / Node / Job | 5s~15s | Resources / Trends |
| 集合通信 | AllReduce/AllGather/ReduceScatter 耗时、带宽效率、通信等待占比 | Job / Node | step~5s | Jobs |
| 数据加载 | DataLoader 迭代耗时、预取队列、CPU→GPU/PPU 拷贝、IO 等待 | Job / Pod | step~5s | Jobs |
| Checkpoint | 保存/恢复耗时、文件大小、写入带宽、异步队列深度、失败次数 | Job | event~5s | Jobs / Alerts |

#### 7.3.3 训练效率与业务运营

| 类别 | 指标 | 默认粒度 | 默认刷新 | 展示页 |
|---|---|---:|---:|---|
| Step 效率 | Step time、P50/P95/P99、前向/反向/优化器/通信/数据加载拆解 | Job | step | Jobs |
| 吞吐 | Tokens/s、Samples/s、每卡吞吐、集群总吞吐 | Job / Accelerator | step | Overview / Jobs |
| MFU / 计算效率 | MFU、实际 TFLOPS、矩阵乘效率 | Job / Accelerator | step | Jobs / Trends |
| 等待与空闲 | GPU/PPU 空闲、等待数据、等待通信、同步屏障等待 | Job / Accelerator | step | Jobs |
| 训练异常 | Loss spike、NaN/Inf、梯度爆炸/消失、LR 异常 | Job | event | Jobs / Alerts |
| 成本 | 卡时、空置卡时、每百万 Token 成本、Goodput、预算消耗 | Job / User / Tenant | 60s~step | Cost & Capacity |
| 调度 | 队列深度、排队时间、资源碎片率、抢占、配额使用率 | Cluster / Tenant | 60s | Overview / Cost & Capacity |

### 7.4 L2 专家诊断指标

默认隐藏，只有以下情况打开：

1. 用户切换 `Expert Mode`。
2. 某个 P1/P2 告警建议打开。
3. 训练任务进入性能调优视图。
4. 新卡型/PPU 适配灰度期。

| 专家指标 | 使用场景 | 采集开销控制 |
|---|---|---|
| SM Occupancy / Warp Occupancy | CUDA kernel 低效定位 | 默认不全量采集，仅对选中 Job 开启 |
| L1/L2/L3 Cache / TLB Miss / IPC | CPU/内存瓶颈定位 | 采样窗口采集 |
| 算子耗时 Top20 / 显存 Top20 | 模型性能优化 | PyTorch Profiler 按计划采样 |
| NCCL Debug / 算法选择 / channel 信息 | 集合通信异常定位 | 仅异常 Job 开启，避免日志洪泛 |
| eBPF syscall / TCP retrans / block IO latency | 系统级瓶颈定位 | 事件触发或短时采样 |
| 显存碎片率 / allocator 细节 | OOM 和显存泄漏 | 需框架 Hook 支持 |

---

## 8. 指标定义与相近指标差异

### 8.1 必须内置 Tooltip 的核心指标

| 指标 | 定义 | 容易混淆的指标 | 差异说明 |
|---|---|---|---|
| 计算利用率 | 采样窗口内加速卡计算单元处于 busy 的比例 | MFU、SM Occupancy | 利用率高表示卡忙，不表示模型计算效率高；MFU 更接近训练有效算力。 |
| MFU | 模型实际 FLOPs / 设备理论峰值 FLOPs | 计算利用率、Tokens/s | MFU 需要模型 FLOPs 和卡型峰值元数据；可用于不同 Job 的效率比较，但跨卡型需谨慎。 |
| 显存使用率 | 已使用显存 / 总显存 | 显存带宽利用率、显存碎片率 | 显存占满不一定慢；带宽高才可能是内存访问瓶颈；碎片率高可能导致 OOM。 |
| 显存带宽利用率 | 实际显存读写带宽 / 理论带宽 | 显存使用率 | 显存使用率是容量，带宽利用率是吞吐压力。 |
| GPU/PPU 空闲时间 | 训练 Step 中设备无有效 kernel/算子执行的时间比例 | 等待通信、等待数据 | 空闲是结果；等待通信/数据是原因拆解。 |
| 通信等待占比 | Step 中因集合通信或同步屏障等待的时间比例 | NCCL AllReduce 耗时 | 单个通信操作耗时高不一定影响总训练；等待占比高才说明阻塞训练。 |
| DataLoader 时间 | 每步数据读取、解码、预处理耗时 | IOWait、CPU 利用率 | DataLoader 是训练视角；IOWait/CPU 是系统视角。 |
| 热节流事件 | 温度超过策略导致降频或限功耗 | 温度、功耗 | 温度高是状态，热节流是性能影响事件。 |
| 卡时 | 分配或使用的卡数量 × 时间 | 空置卡时、Goodput | 卡时是成本口径；Goodput 衡量有效训练时间占比。 |
| 资源碎片率 | 因卡型/拓扑/配额导致无法调度的剩余资源比例 | 空闲卡数 | 有空闲卡不代表能调度大 Job；碎片率解释“有卡但排队”。 |

### 8.2 Tooltip 交互内容模板

```text
指标名：MFU
定义：模型实际 FLOPs / 当前卡型理论峰值 FLOPs。
单位：%
默认聚合：Job 内按 step 时间加权平均；跨 Job 默认不直接平均，需按 token 或 step 加权。
相近指标差异：
- 与 GPU 利用率不同：GPU 利用率反映设备忙闲，MFU 反映有效模型计算效率。
- 与 Tokens/s 不同：Tokens/s 是业务吞吐，受 batch、seq length、并行策略影响。
采集来源：Training Hook + 卡型峰值元数据。
常见异常：GPU 利用率高但 MFU 低，通常意味着 kernel 效率低、通信等待、padding 浪费或并行策略不合理。
```

---

## 9. 过滤设计

### 9.1 过滤器分层

| 层级 | 过滤器 | 作用范围 | UI 形态 |
|---|---|---|---|
| 全局过滤 | 时间范围、Region、Cluster、租户、卡型 | 全部 Tab | 顶部 Filter Bar |
| 页面过滤 | 当前 Tab 的业务过滤，如 Job 状态、告警等级、成本口径 | 当前 Tab | Tab 内容顶部 |
| Card 过滤 | 单个 Card 的 group by、TopN、阈值 | 当前 Card | Card header mini controls |
| 图表交互过滤 | brush 时间段、legend 开关、点击点位 | 当前图或联动 Drawer | 图表内交互 |

### 9.2 维度过滤

| 维度 | 交互 | 参数名 | 示例 |
|---|---|---|---|
| Region | 多选、收藏、排除 | `region_ids` | `['cn-hangzhou', 'cn-wulanchabu']` |
| Cluster | 多选、搜索 | `cluster_ids` | `['train-prod-a']` |
| 卡型 | 多选、按供应商分组 | `accelerator_models` | `['H200', 'RTX_PRO_5000_BLACKWELL', 'ZHENWU_810E']` |
| 供应商 | 多选 | `vendors` | `['nvidia', 'aliyun_ppu']` |
| 健康状态 | 快捷 chip | `health_status` | `['warning', 'critical']` |
| Node | 搜索、多选 | `node_ids` | `['node-123']` |
| Job | 搜索、多选、最近访问 | `job_ids` | `['job-abc']` |
| 租户/用户 | 多选 | `tenant_ids`, `user_ids` | `['team-a']` |
| 运行框架 | 多选 | `frameworks` | `['Megatron', 'DeepSpeed', 'FSDP']` |
| 并行策略 | 多选 | `parallel_strategies` | `['DP', 'TP', 'PP', 'ZeRO']` |
| 网络类型 | 多选 | `network_types` | `['RoCE', 'IB', 'NVLink']` |

### 9.3 指标值过滤

指标值过滤用于“从海量单卡/Job 中找问题”，支持条件表达式：

```text
metric(operator)value
metric BETWEEN min AND max
metric RATE_GT value PER window
metric INCREASE_GT value PER window
metric DEVIATE_GT baseline_pct
metric RANK_TOP n BY metric
```

常用预设：

| 预设名称 | 条件表达式 | 典型用途 |
|---|---|---|
| 分配但低利用 | `allocated=true AND accelerator.utilization.compute.pct < 20 FOR 15m` | 找占卡不用 |
| 高显存低计算 | `memory.used.pct > 80 AND compute.utilization.pct < 30 FOR 10m` | 找数据/通信/等待问题 |
| 热节流 | `thermal.throttle.events > 0 OR power.limit.hit.pct > 5` | 找性能降频 |
| 通信瓶颈 | `training.wait.communication.pct > 25 OR nccl.allreduce.duration.p95 > baseline*1.2` | 找 NCCL/网络问题 |
| IO 瓶颈 | `training.wait.data.pct > 20 OR dataloader.iteration.ms.p95 > baseline*1.2` | 找数据加载问题 |
| 硬件风险 | `xid.errors.increase > 0 OR ecc.uncorrectable.increase > 0 OR device.offline.events > 0` | 找故障卡 |
| 成本异常 | `cost.per_million_tokens > baseline*1.3 OR goodput.pct < 70` | 找训练成本异常 |

### 9.4 过滤结果的可解释性

每次应用过滤后，页面显示一句自然语言摘要：

```text
当前筛选：过去 6 小时，杭州 + 乌兰察布，H200 + 真武 810E，已分配但计算利用率 < 20% 持续 15 分钟。
命中：143 张卡，涉及 18 个 Job、42 个 Node、3 个租户。
```

---

## 10. 汇总与趋势分析

### 10.1 聚合函数

| 函数 | 适用指标 | 说明 |
|---|---|---|
| `sum` | 卡时、错误次数、吞吐量、成本 | 累计类指标。 |
| `avg` | 利用率、温度、功耗 | 单维平均，需注意是否加权。 |
| `weighted_avg` | 跨卡型利用率、MFU、显存使用率 | 按采样数、卡时、显存容量或 token 加权。 |
| `min/max` | 温度、功耗、显存、Step time | 极值定位。 |
| `p50/p95/p99` | Step time、延迟、DataLoader、通信耗时 | 长尾分析。 |
| `rate` | counter 型错误、网络包、IO bytes | 单位时间速率。 |
| `increase` | Xid/ECC/OOM/重启 | 时间窗口内增量。 |
| `topn/bottomn` | 利用率、成本、告警数、等待占比 | 排名。 |
| `distribution` | 利用率分布、温度分布、排队时间分布 | 直方图/箱线图。 |
| `baseline_deviation` | Step time、Tokens/s、MFU、通信耗时 | 与历史或同类基线对比。 |

### 10.2 维度汇总

| 汇总视角 | 示例问题 | 默认展示 |
|---|---|---|
| Region | 哪个 Region 故障多、利用率低？ | Region 横向对比 Card |
| 卡型 | H200 vs PPU vs RTX PRO 5000 表现差异？ | 卡型矩阵 + 趋势 |
| 租户 | 哪个团队卡时高但效率低？ | 租户 TopN |
| Job | 哪些 Job 拖慢集群？ | Job TopN |
| Node | 哪些节点异常集中？ | Node TopN + 热力图 |
| 时间 | 今天是否比昨天变差？ | 趋势图 + 基线偏离 |
| 框架/并行策略 | DeepSpeed/FSDP/Megatron 的效率差异？ | 训练效率分组图 |

### 10.3 趋势分析

趋势分析必须覆盖两类：

1. **单卡明细时间序列**：`accelerator_id` 固定，展示计算利用率、显存、温度、功耗、错误、关联 Job/Pod。
2. **维度汇总时间序列**：按 `region / model / tenant / job / node / framework` 聚合后的时间序列。

趋势图交互：

| 交互 | 说明 |
|---|---|
| 时间范围 | 15m、1h、6h、24h、7d、自定义。 |
| 分辨率 | Auto、1s、5s、15s、1m、5m。 |
| Group By | Region、卡型、Job、租户、Node、框架。 |
| Compare | 同比昨天、环比上小时、同类卡型基线。 |
| Brush | 框选异常时间段后自动带入下方事件列表。 |
| Overlay | 叠加告警、Job 阶段、Checkpoint、Pod 重启、调度事件。 |

### 10.4 汇总公式示例

#### 跨 Region 计算利用率

```text
global_compute_util =
  sum(region_compute_util_avg * region_active_card_sample_count)
  / sum(region_active_card_sample_count)
```

#### 显存使用率

```text
memory_used_pct =
  sum(memory_used_bytes) / sum(memory_total_bytes) * 100
```

#### 卡时

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

## 11. 页面与功能设计

## 11.1 Overview：总览页

### 11.1.1 页面目标

让用户 10 秒内知道：当前整体是否健康、哪个 Region/卡型/Job 有问题、资源是否浪费、要点哪里下钻。

### 11.1.2 页面结构

```text
Overview
├─ Hero Summary Band
│  ├─ 全局健康标题
│  ├─ 时间范围 / 刷新状态
│  └─ 4 个主 KPI：可用卡、活跃卡、平均利用率、P0 告警
├─ Global Filter Bar
├─ Health & Utilization Cards
├─ Region × Accelerator Model Matrix
├─ TopN Cards
│  ├─ 异常卡 TopN
│  ├─ 低利用 Job TopN
│  ├─ 热/功耗风险 Node TopN
│  └─ 成本浪费 TopN
└─ Event Timeline
```

### 11.1.3 Card 设计

| Card | 内容 | 点击后 |
|---|---|---|
| Global Health | 健康卡占比、异常卡数、P0/P1 告警数 | 打开 Alerts，自动过滤 P0/P1 |
| Utilization | 平均计算利用率、显存使用率、活跃卡数 | 打开 Trends，group by Region |
| Availability | 总卡数、可用卡、不可用卡、掉卡事件 | 打开 Resources，过滤 unhealthy |
| Cost Waste | 空置卡时、低利用卡时、估算浪费成本 | 打开 Cost & Capacity |
| Region × Card Matrix | 每个 Region/卡型的健康、利用、分配率 | 点击单元格进入 Resources 过滤 |
| Top Abnormal Accelerators | 异常单卡 TopN | 打开单卡 Detail Drawer |
| Top Slow Jobs | Step time 退化 / 通信等待 / IO 等待 TopN | 打开 Job Detail Drawer |

---

## 11.2 Resources：算力资源页

### 11.2.1 页面目标

支持从 Region、Cluster、Node、单卡三个层级查看资源详情，并能定位硬件和系统问题。

### 11.2.2 页面结构

```text
Resources
├─ Resource Filter Bar
├─ Inventory Summary Cards
├─ Resource Table
│  ├─ Region / Cluster / Node / Accelerator 分层视图
│  ├─ 列配置
│  └─ 指标值过滤
├─ Resource Trend Panel
└─ Accelerator Detail Drawer
```

### 11.2.3 资源表字段

| 字段 | 说明 |
|---|---|
| 状态 | Healthy / Warning / Critical / Offline |
| Region / Cluster / Node | 位置维度 |
| 卡型 | H200 / RTX PRO 5000 / 真武 810E / 真武 M890 / 自定义 |
| 供应商 | NVIDIA / Alibaba PPU / Generic |
| 当前 Job | 正在绑定的任务，支持点击跳转 |
| 计算利用率 | 当前值 + 过去 15m Sparkline |
| 显存使用率 | 当前值 + 峰值 |
| 温度 / 功耗 | 当前值 + 阈值状态 |
| 错误 | Xid/ECC/掉卡/PPU error 数 |
| 网络 | NVLink/PCIe/NIC 状态 |
| 采集状态 | exporter healthy / stale / missing |

### 11.2.4 单卡 Detail Drawer

Drawer 宽度 560px，右侧滑出。内容：

1. 卡身份：`accelerator_id`、vendor、model、uuid、Region、Node、device index。
2. 状态摘要：健康、当前 Job、采集状态、最近事件。
3. 核心曲线：计算利用率、显存、显存带宽、温度、功耗。
4. 运行绑定：Pod、Container、Process、Job、租户。
5. 事件时间线：告警、Xid/ECC、掉卡、Pod 重启、Checkpoint。
6. 相近指标解释：GPU 利用率 vs MFU vs SM Occupancy。
7. 操作：复制资源 ID、打开 Job、创建告警规则、导出时间段、标记维护。

---

## 11.3 Jobs：训练任务分析页

### 11.3.1 页面目标

让训练工程师能判断 Job 慢在哪里：计算、通信、数据、Checkpoint、调度、硬件异常还是代码/模型行为。

### 11.3.2 页面结构

```text
Jobs
├─ Job Search / Filter
├─ Job Summary Cards
│  ├─ 状态 / 运行时长
│  ├─ Tokens/s / Samples/s
│  ├─ Step time P50/P95/P99
│  ├─ MFU / Goodput
│  └─ 成本 / 卡时
├─ Step Time Breakdown
├─ Accelerator Skew Matrix
├─ Communication & IO Analysis
├─ Loss / LR / NaN Trend
└─ Job Event Timeline
```

### 11.3.3 Step Time 拆解

| 拆解项 | 来源 | 用途 |
|---|---|---|
| Forward | 框架 Hook / Profiler | 模型前向耗时 |
| Backward | 框架 Hook / Profiler | 反向传播耗时 |
| Optimizer | 框架 Hook | 优化器耗时 |
| Communication | NCCL / 框架 Hook | 梯度同步、集合通信 |
| Data Loading | DataLoader Hook / IO 指标 | 数据瓶颈 |
| Checkpoint | Checkpoint Hook | 保存/恢复影响 |
| Idle / Barrier | Runtime Hook | 同步等待、长尾卡拖慢 |

### 11.3.4 Accelerator Skew Matrix

矩阵行是 `node_id`，列是 `device_index`，每格显示：

- Step time 相对 Job 中位数偏差。
- 计算利用率。
- 通信等待占比。
- Data wait 占比。
- 异常事件角标。

颜色规则：

| 状态 | 条件 | 颜色 |
|---|---|---|
| 正常 | 偏差 < 10% | mint/green |
| 轻微拖慢 | 10%~20% | yellow |
| 明显拖慢 | 20%~50% | orange |
| 严重拖慢 | >50% 或有 P0 事件 | red |

---

## 11.4 Trends：趋势分析页

### 11.4.1 页面目标

支持跨 Region、卡型、租户、Job 的时间趋势对比，兼顾单卡明细和汇总趋势。

### 11.4.2 页面结构

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

### 11.4.3 查询示例

```text
过去 24 小时，Region=杭州/乌兰察布，卡型=H200/真武810E，
按 card_type + region group by，查看平均计算利用率、P95 Step time、硬件错误次数。
```

### 11.4.4 图表能力

| 图表 | 用途 |
|---|---|
| 折线图 | 多 Region/卡型趋势比较 |
| 面积图 | 卡时、成本、吞吐累计趋势 |
| 热力图 | Node/卡负载分布 |
| 箱线图 | Step time / 利用率分布 |
| 排名变化图 | TopN Job/租户随时间变化 |
| 散点图 | 利用率 vs 成本、MFU vs Tokens/s |

---

## 11.5 Alerts：告警事件页

### 11.5.1 页面目标

完成告警发现、确认、定位、关联指标、复发判断和规则优化。

### 11.5.2 告警列表字段

| 字段 | 说明 |
|---|---|
| Severity | P0/P1/P2/P3 |
| 状态 | Firing / Acknowledged / Silenced / Resolved |
| 告警名称 | 如 `AcceleratorOffline`, `XidError`, `LowUtilizationAllocated` |
| 资源 | Region / Node / Accelerator / Job |
| 当前值 | 触发时指标值 |
| 阈值 | 固定阈值或基线偏离 |
| 首次出现 | `first_seen` |
| 最近出现 | `last_seen` |
| 关联事件 | Pod 重启、Checkpoint、网络事件 |
| 建议动作 | 打开单卡详情、隔离节点、联系租户、扩容等 |

### 11.5.3 告警规则模板

| 模板 | 条件 | 默认等级 |
|---|---|---|
| 单卡离线 | `device.offline.events > 0` | P0 |
| 不可纠正 ECC | `ecc.uncorrectable.increase > 0` | P0 |
| Xid 错误 | `xid.errors.increase > 0` | P0/P1 |
| 热节流 | `thermal.throttle.events > 0 FOR 5m` | P1 |
| 分配低利用 | `allocated=true AND compute.utilization.pct < 20 FOR 30m` | P1 |
| 通信等待异常 | `training.wait.communication.pct > 30 FOR 10m` | P1 |
| DataLoader 异常 | `training.wait.data.pct > 25 FOR 10m` | P1 |
| 队列积压 | `queue.pending_time.p95 > SLO FOR 15m` | P1/P2 |
| 成本超预算 | `cost.budget_used.pct > threshold` | P2 |

---

## 11.6 Cost & Capacity：成本与容量页

### 11.6.1 页面目标

把算力消耗转化为运营指标：卡时、空置卡时、低利用率成本、Goodput、队列、资源碎片和容量水位。

### 11.6.2 核心 Card

| Card | 指标 | 下钻 |
|---|---|---|
| Card-hours | GPU/PPU 卡时、分配卡时、活跃卡时 | 按 Region/租户/Job |
| Waste | 空置卡时、分配低利用卡时、估算浪费 | Top 低效 Job/租户 |
| Goodput | 有效训练时间占比 | Job 明细 |
| Queue | 排队时间 P50/P95、队列深度 | 调度失败原因 |
| Fragmentation | 资源碎片率、不可调度剩余资源 | Region/卡型/拓扑 |
| Capacity Watermark | 7d/30d 水位、峰值、预测 | 扩容建议 |

---

## 11.7 Settings：指标与配置页

### 11.7.1 设置项

| 配置 | 说明 |
|---|---|
| 指标字典 | 指标启停、名称、单位、定义、相近指标、来源、优先级。 |
| 采集 Profile | Basic / Standard / Expert；按 Region/卡型/租户配置。 |
| 阈值模板 | 全局阈值、按卡型阈值、按租户阈值、基线规则。 |
| 视图模板 | Overview、Job、Resource 的保存视图。 |
| Adapter 管理 | NVIDIA、PPU、自定义 exporter 的健康与映射。 |
| 权限 | 哪些用户可看成本、租户、单卡详情、告警操作。 |

### 11.7.2 采集 Profile

| Profile | 面向场景 | 采集内容 | 默认策略 |
|---|---|---|---|
| Basic | 值班与容量 | P0 核心：健康、利用率、显存、温度、功耗、错误、K8s 状态 | 全量开启 |
| Standard | 日常排障 | P1：网络、通信、Step time、吞吐、数据加载、Checkpoint、成本 | 训练集群默认开启 |
| Expert | 性能调优 | P2：Profiler、算子、SM/Warp、eBPF、NCCL debug | 按 Job/时间窗口开启 |

---

# 12. 独立 UI 设计章节

## 12.1 设计风格总原则

视觉完全参考 Notion：白色 canvas、温和灰色 surface、低饱和 pastel card、深 navy hero band、紫色主按钮、Notion Sans 字体、8px 矩形按钮、12px 卡片圆角、细 hairline 边框、轻量阴影。

### 12.1.1 Design Tokens

| Token | 值 | 使用 |
|---|---|---|
| `colors.primary` | `#5645d4` | 主 CTA、选中态强调，不做大面积背景。 |
| `colors.brand-navy` | `#0a1530` | Overview 顶部 hero summary band。 |
| `colors.canvas` | `#ffffff` | 主页面和 Card 背景。 |
| `colors.surface` | `#f6f5f4` | 页面背景、搜索栏、浅色分区。 |
| `colors.hairline` | `#e5e3df` | Card、表格、分割线。 |
| `colors.ink` | `#1a1a1a` | 正文主色。 |
| `colors.charcoal` | `#37352f` | 标题和重要文本。 |
| `colors.steel` | `#787671` | 次级文本。 |
| `colors.semantic-success` | `#1aae39` | 正常/恢复。 |
| `colors.semantic-warning` | `#dd5b00` | 警告。 |
| `colors.semantic-error` | `#e03131` | 严重错误。 |

### 12.1.2 字体

```css
font-family: "Notion Sans", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

| 层级 | 字号 | 字重 | 行高 | 用途 |
|---|---:|---:|---:|---|
| Page Title | 36px | 600 | 1.20 | Tab 页标题 |
| Section Title | 22px | 600 | 1.30 | Card 组标题 |
| Card Title | 16px | 600 | 1.40 | 单 Card 标题 |
| Metric Value | 28px | 600 | 1.15 | KPI 数值 |
| Body | 14px | 400 | 1.50 | 表格、描述 |
| Caption | 12~13px | 500/600 | 1.40 | Badge、说明 |

### 12.1.3 圆角与边框

| 组件 | 圆角 | 边框 |
|---|---:|---|
| Button | 8px | secondary 使用 `1px solid #c8c4be` |
| Card | 12px | `1px solid #e5e3df` |
| Input / Search | 8px | `1px solid #c8c4be`，focus `2px solid #5645d4` |
| Pill Tab | 9999px | inactive `1px solid #e5e3df` |
| Drawer | 16px 左上/左下 | `1px solid #e5e3df` |
| Badge | 9999px 或 6px | 无或浅色边框 |

---

## 12.2 全局页面布局：Desktop 1440 × 900

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

| 属性 | 值 |
|---|---|
| 高度 | 64px |
| 背景 | `#ffffff` |
| 边框 | bottom `1px solid #e5e3df` |
| 左侧 | Logo 32px、产品名、当前环境 Badge |
| 中间 | 全局搜索，宽 420px，高 44px，背景 `#f6f5f4` |
| 右侧 | 时间范围、刷新按钮、导出按钮、用户头像 |
| 字体 | 14px / 500 |

### 12.2.3 Left Rail

| 属性 | 值 |
|---|---|
| 宽度 | 248px |
| 背景 | `#fafaf9` |
| 边框 | right `1px solid #e5e3df` |
| 内边距 | 16px 12px |
| 分区 | Favorites、Regions、Views、Recent Jobs |
| Item 高度 | 36px |
| Item 圆角 | 6px |
| Active 背景 | `#f0eeec` |

### 12.2.4 Main Content

| 属性 | 值 |
|---|---|
| 背景 | `#ffffff` |
| 最大内容宽 | 1280px |
| 左右内边距 | 32px |
| 顶部内边距 | 24px |
| Card 间距 | 16px |
| Grid | 12 columns，gutter 16px |

---

## 12.3 Overview 页面像素级布局

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

| 属性 | 值 |
|---|---|
| 位置 | Main content 顶部 |
| 尺寸 | 宽 100%，高 180px |
| 背景 | `#0a1530` |
| 圆角 | 16px |
| 内边距 | 32px |
| 装饰 | 右上角 8~12 个 pastel sticky dots，透明度 0.9；不影响数据阅读 |
| 标题 | 36px / 600 / white |
| 副标题 | 14px / `#a4a097` |
| 右侧 | 刷新状态、数据完整性 Badge、当前时间范围 |

Hero 内部右侧放一个 `workspace-mockup-card` 风格白色摘要卡：

| 属性 | 值 |
|---|---|
| 尺寸 | 420px × 132px |
| 背景 | `#ffffff` |
| 圆角 | 12px |
| 阴影 | `rgba(15,15,15,0.20) 0px 24px 48px -8px` |
| 内容 | 4 个 mini KPI：Healthy、Active、Alerts、Waste |

### 12.3.2 Pill Tab Row

| 属性 | 值 |
|---|---|
| 高度 | 44px |
| 顶部间距 | 24px |
| Tab 高度 | 32px |
| Inactive | 文字 `#787671`，边框 `#e5e3df`，圆角 9999px |
| Active | 背景 `#000000`，文字 `#ffffff` |
| Tab 间距 | 8px |

### 12.3.3 Filter Bar

| 属性 | 值 |
|---|---|
| 高度 | 56px |
| 背景 | `#f6f5f4` |
| 圆角 | 12px |
| 内边距 | 8px 12px |
| 组件 | Region Select、Card Type Select、Tenant Select、Metric Condition、Group By、Reset |
| Select 高度 | 40px |
| 搜索输入 | 240px × 40px |
| Chip | 28px 高，圆角 9999px |

### 12.3.4 KPI Cards

4 个主卡片，每个宽 `(1192 - 3*16)/4 = 286px`，高 132px。

| 元素 | 样式 |
|---|---|
| Card 背景 | `#ffffff` |
| 边框 | `1px solid #e5e3df` |
| 圆角 | 12px |
| Padding | 20px |
| Title | 13px / 600 / `#787671` |
| Value | 28px / 600 / `#1a1a1a` |
| Delta | 13px badge，绿色/橙色/红色 |
| Sparkline | 右下角 88px × 28px |

KPI 卡颜色只用于 badge 和小图，不做大面积高饱和背景。

### 12.3.5 Matrix Card

| 属性 | 值 |
|---|---|
| 尺寸 | 776px × 360px，占 8 columns |
| 标题 | `Region × Card Type` |
| 表头高度 | 40px |
| 单元格 | 96px × 64px |
| 单元格内容 | 健康率、平均利用率、P0 count |
| 色阶 | pastel mint/yellow/peach/rose，不用刺眼红绿大块 |
| 点击 | 点击单元格应用过滤并打开 Resources |

### 12.3.6 TopN Card

| 属性 | 值 |
|---|---|
| 尺寸 | 400px × 360px，占 4 columns |
| Tab | Abnormal / Low Util / Slow Jobs / Cost |
| 行高 | 44px |
| 行内容 | 排名、资源名、Region、指标值、趋势箭头 |
| 点击 | 打开 Detail Drawer |

### 12.3.7 Detail Drawer

| 属性 | 值 |
|---|---|
| 宽度 | 560px |
| 高度 | 100vh |
| 位置 | right: 0, top: 0 |
| 背景 | `#ffffff` |
| 边框 | left `1px solid #e5e3df` |
| 阴影 | `rgba(15,15,15,0.16) 0px 16px 48px -8px` |
| Header 高度 | 72px |
| 内容 padding | 24px |
| 关闭按钮 | 32px × 32px，ghost |
| API | 打开时拉取资源详情、趋势、事件、指标说明 |

---

## 12.4 组件交互行为与 API 绑定

### 12.4.1 API 通用约定

| 项 | 约定 |
|---|---|
| Base URL | `/api/v1/monitor` |
| 鉴权 | 继承平台登录态，所有接口校验 workspace/tenant/resource 权限 |
| 时间参数 | `start_time`, `end_time` 使用 ISO8601 UTC；前端本地化展示 |
| 分辨率 | `resolution=auto|1s|5s|15s|1m|5m|1h` |
| 请求方式 | 查询类复杂条件统一 POST；轻量 metadata GET |
| 响应状态 | 统一包含 `data_status: complete|partial|stale|empty` |
| 错误处理 | Region 级 partial 不阻塞全局返回 |

### 12.4.2 页面加载与全局交互 API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 关键参数 |
|---|---|---|---|---|---|
| 打开 SPA | GetBootstrap | GET | `/bootstrap` | 获取用户权限、默认视图、默认时间范围、可访问 Region | `workspace_id` |
| 获取 Region 列表 | ListRegions | GET | `/meta/regions` | 返回可访问 Region 及状态 | `workspace_id`, `include_status` |
| 获取卡型列表 | ListAcceleratorTypes | GET | `/meta/accelerator-types` | 返回 vendor/model/capability | `region_ids[]`, `vendors[]` |
| 获取指标字典 | ListMetricDictionary | GET | `/metrics/dictionary` | 返回指标定义、单位、Tooltip、相近指标 | `layer`, `priority`, `vendor`, `model` |
| 全局搜索 | GlobalSearch | GET | `/search` | 搜索 Job/Node/Accelerator/Alert | `q`, `types[]`, `limit` |
| 修改时间范围 | QueryOverviewSummary | POST | `/overview/summary` | 按新时间范围刷新 Overview KPI | `start_time`, `end_time`, `filters` |
| 点击刷新 | RefreshCurrentView | POST | `/views/current/refresh` | 根据当前视图配置刷新数据 | `view_id`, `force`, `last_query_token` |
| 保存当前视图 | SaveView | POST | `/views` | 保存过滤器、图表、列配置 | `name`, `tab`, `filters`, `layout`, `visibility` |
| 导出当前结果 | ExportView | POST | `/export` | 导出 CSV/PNG/Markdown 报告 | `view_id`, `format`, `scope`, `time_range` |

### 12.4.3 Tab 切换 API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 参数 |
|---|---|---|---|---|---|
| 切到 Overview | QueryOverviewSummary | POST | `/overview/summary` | 获取总览 KPI、矩阵、TopN 摘要 | `time_range`, `filters` |
| 切到 Resources | QueryResourceInventory | POST | `/resources/query` | 获取资源表和库存摘要 | `time_range`, `filters`, `page`, `sort` |
| 切到 Jobs | QueryJobs | POST | `/jobs/query` | 获取 Job 列表和任务摘要 | `time_range`, `filters`, `page`, `sort` |
| 切到 Trends | InitMetricExplorer | GET | `/trends/config` | 获取可选指标、聚合、group by 配置 | `tab=trends`, `vendor`, `model` |
| 切到 Alerts | SearchAlerts | POST | `/alerts/search` | 获取告警列表 | `time_range`, `severity[]`, `status[]`, `filters` |
| 切到 Cost | QueryCostCapacitySummary | POST | `/cost-capacity/summary` | 获取成本、卡时、队列、水位 | `time_range`, `filters`, `cost_mode` |
| 切到 Settings | GetSettings | GET | `/settings` | 获取指标、阈值、采集 Profile 配置 | `workspace_id` |

### 12.4.4 过滤器 API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 参数 |
|---|---|---|---|---|---|
| 打开 Region 下拉 | ListRegions | GET | `/meta/regions` | 获取 Region 选项和状态 | `q`, `workspace_id` |
| 打开 Cluster 下拉 | ListClusters | GET | `/meta/clusters` | 获取 Cluster 选项 | `region_ids[]`, `q` |
| 打开卡型下拉 | ListAcceleratorTypes | GET | `/meta/accelerator-types` | 获取卡型选项 | `region_ids[]`, `vendor[]` |
| 打开 Job 下拉 | SearchJobs | GET | `/meta/jobs/search` | 搜索 Job | `q`, `time_range`, `tenant_ids[]` |
| 打开租户下拉 | ListTenants | GET | `/meta/tenants` | 获取租户 | `q`, `workspace_id` |
| 添加维度过滤 | QueryCurrentTabData | POST | `/query/current-tab` | 使用新 filters 刷新当前 Tab | `tab`, `filters`, `time_range`, `layout` |
| 添加指标值过滤 | ValidateMetricFilter | POST | `/filters/metric/validate` | 校验表达式合法性 | `expression`, `metric_id` |
| 应用指标值过滤 | QueryCurrentTabData | POST | `/query/current-tab` | 后端执行指标值过滤 | `metric_filters[]`, `filters`, `time_range` |
| 重置过滤 | QueryCurrentTabData | POST | `/query/current-tab` | 使用默认过滤器刷新 | `tab`, `default_filters=true` |
| 保存过滤预设 | SaveFilterPreset | POST | `/filters/presets` | 保存常用过滤条件 | `name`, `filters`, `metric_filters` |

### 12.4.5 Overview Card API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 参数 |
|---|---|---|---|---|---|
| 加载 4 个主 KPI | QueryOverviewSummary | POST | `/overview/summary` | 返回健康、利用率、成本、告警摘要 | `time_range`, `filters`, `compare_mode` |
| 加载 Region × 卡型矩阵 | QueryRegionModelMatrix | POST | `/overview/region-model-matrix` | 返回每个单元格的健康率、利用率、告警数 | `time_range`, `filters`, `metrics[]` |
| 点击矩阵单元格 | QueryResourceInventory | POST | `/resources/query` | 进入 Resources 并带过滤 | `region_id`, `accelerator_model`, `time_range` |
| 加载异常 TopN | QueryTopN | POST | `/query/topn` | 返回异常卡/Job/Node TopN | `metric_id`, `rank_by`, `n`, `filters` |
| 切换 TopN Tab | QueryTopN | POST | `/query/topn` | 按所选类型刷新 TopN | `topn_type`, `time_range`, `filters` |
| 点击 TopN 行 | GetResourceDetail / GetJobDetail | GET | `/resources/{id}` 或 `/jobs/{id}` | 打开详情 Drawer | `id`, `time_range` |
| 加载事件时间线 | QueryEventTimeline | POST | `/events/timeline` | 返回告警、K8s、Checkpoint、硬件事件 | `time_range`, `filters`, `event_types[]` |

### 12.4.6 Resources API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 参数 |
|---|---|---|---|---|---|
| 加载资源表 | QueryResourceInventory | POST | `/resources/query` | 分页查询 Region/Node/Accelerator | `filters`, `columns[]`, `page`, `page_size`, `sort` |
| 切换层级视图 | QueryResourceInventory | POST | `/resources/query` | 按 Region/Cluster/Node/Accelerator 聚合 | `view_level`, `group_by[]`, `filters` |
| 排序表格 | QueryResourceInventory | POST | `/resources/query` | 服务端排序 | `sort_by`, `sort_order` |
| 自定义列 | SaveTableColumns | POST | `/settings/table-columns` | 保存列配置 | `tab`, `columns[]` |
| 打开单卡 Drawer | GetAcceleratorDetail | GET | `/resources/accelerators/{accelerator_id}` | 返回单卡身份、状态、能力 | `accelerator_id` |
| 拉取单卡趋势 | QueryMetricRange | POST | `/query/range` | 返回单卡多指标时间序列 | `metric_ids[]`, `filters.accelerator_id`, `time_range`, `resolution` |
| 拉取单卡事件 | QueryEventTimeline | POST | `/events/timeline` | 返回单卡事件 | `resource_type=accelerator`, `resource_id`, `time_range` |
| 标记维护 | MarkResourceMaintenance | POST | `/resources/maintenance` | 将资源置为维护状态 | `resource_type`, `resource_id`, `reason`, `until` |
| 创建资源告警规则 | CreateAlertRule | POST | `/alerts/rules` | 基于当前资源创建规则 | `metric_id`, `resource_selector`, `condition`, `severity` |

### 12.4.7 Jobs API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 参数 |
|---|---|---|---|---|---|
| 加载 Job 列表 | QueryJobs | POST | `/jobs/query` | 查询 Job 列表 | `filters`, `metric_filters`, `page`, `sort` |
| 搜索 Job | SearchJobs | GET | `/meta/jobs/search` | 按名称/ID/用户搜索 | `q`, `time_range`, `tenant_ids[]` |
| 打开 Job 详情 | GetJobDetail | GET | `/jobs/{job_id}` | 返回任务元数据、资源绑定、状态 | `job_id` |
| 获取 Job 摘要 | GetJobSummary | GET | `/jobs/{job_id}/summary` | 返回吞吐、Step、MFU、Goodput、成本 | `job_id`, `start_time`, `end_time` |
| 获取 Step 拆解 | QueryJobStepBreakdown | POST | `/jobs/{job_id}/step-breakdown` | 返回前向/反向/通信/IO 拆解 | `job_id`, `time_range`, `aggregation` |
| 获取单卡 skew 矩阵 | QueryJobAcceleratorSkew | POST | `/jobs/{job_id}/accelerator-skew` | 返回每张卡相对偏差 | `job_id`, `metric_ids[]`, `time_range` |
| 获取通信分析 | QueryJobCommunication | POST | `/jobs/{job_id}/communication` | 返回 NCCL/集合通信指标 | `job_id`, `collective_types[]`, `time_range` |
| 获取 IO 分析 | QueryJobIO | POST | `/jobs/{job_id}/io` | 返回 DataLoader/存储/拷贝指标 | `job_id`, `time_range` |
| 获取训练异常 | QueryTrainingAnomalies | POST | `/jobs/{job_id}/anomalies` | 返回 loss spike、NaN/Inf 等 | `job_id`, `time_range`, `types[]` |
| 开启短时 Profiler | StartProfilerSession | POST | `/jobs/{job_id}/profiler/sessions` | 对指定 Job 开启专家采样 | `job_id`, `duration_seconds`, `profile_items[]` |
| 获取 Profiler 结果 | GetProfilerSession | GET | `/jobs/{job_id}/profiler/sessions/{session_id}` | 返回算子 TopN、trace 状态 | `job_id`, `session_id` |

### 12.4.8 Trends / Metric Explorer API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 参数 |
|---|---|---|---|---|---|
| 打开指标选择器 | ListMetricDictionary | GET | `/metrics/dictionary` | 指标列表与定义 | `layer`, `priority`, `scope`, `vendor` |
| 查询单指标趋势 | QueryMetricRange | POST | `/query/range` | 返回时间序列 | `metric_id`, `filters`, `time_range`, `resolution` |
| 查询多指标趋势 | QueryMultiMetricRange | POST | `/query/range/multi` | 返回多指标多 series | `metric_ids[]`, `filters`, `group_by[]` |
| 查询汇总趋势 | QueryRollupRange | POST | `/query/rollup-range` | 返回按 group by 聚合的趋势 | `metric_id`, `aggregation`, `group_by[]`, `filters` |
| 查询分布 | QueryDistribution | POST | `/query/distribution` | 返回直方图/箱线图 | `metric_id`, `bucket`, `filters`, `time_range` |
| 查询 TopN 趋势 | QueryTopNOverTime | POST | `/query/topn-over-time` | 返回排名随时间变化 | `metric_id`, `n`, `group_by`, `time_range` |
| 添加基线对比 | QueryCompare | POST | `/query/compare` | 同比/环比/同类基线 | `metric_id`, `compare_mode`, `baseline_selector` |
| 图表 brush | QueryDrilldownByTimeRange | POST | `/query/drilldown` | 按框选时间查询事件和明细 | `time_range`, `filters`, `metric_context` |

### 12.4.9 Alerts API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 参数 |
|---|---|---|---|---|---|
| 加载告警列表 | SearchAlerts | POST | `/alerts/search` | 分页查询告警 | `time_range`, `severity[]`, `status[]`, `filters`, `page` |
| 打开告警详情 | GetAlertDetail | GET | `/alerts/{alert_id}` | 返回告警详情、规则、关联事件 | `alert_id` |
| 确认告警 | AckAlert | PATCH | `/alerts/{alert_id}` | 状态改为 acknowledged | `status`, `comment` |
| 静默告警 | SilenceAlert | POST | `/alerts/silences` | 创建静默规则 | `matcher`, `start_time`, `end_time`, `reason` |
| 恢复告警 | ResolveAlert | PATCH | `/alerts/{alert_id}` | 手动恢复 | `status=resolved`, `comment` |
| 创建规则 | CreateAlertRule | POST | `/alerts/rules` | 创建告警规则 | `name`, `metric_id`, `condition`, `filters`, `severity` |
| 更新规则 | UpdateAlertRule | PATCH | `/alerts/rules/{rule_id}` | 修改规则 | `condition`, `severity`, `enabled` |
| 测试规则 | TestAlertRule | POST | `/alerts/rules/test` | 返回历史命中情况 | `condition`, `filters`, `time_range` |

### 12.4.10 Cost & Capacity API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 参数 |
|---|---|---|---|---|---|
| 加载成本摘要 | QueryCostCapacitySummary | POST | `/cost-capacity/summary` | 卡时、成本、Goodput、队列 | `time_range`, `filters`, `cost_model` |
| 成本分组 | QueryCostBreakdown | POST | `/cost-capacity/breakdown` | 按 Region/租户/Job/卡型分组 | `group_by[]`, `metrics[]`, `filters` |
| 低效 TopN | QueryWasteTopN | POST | `/cost-capacity/waste-topn` | 低利用卡时/Job/租户 TopN | `n`, `rank_by`, `filters` |
| 队列分析 | QueryQueueMetrics | POST | `/cost-capacity/queue` | 排队时间、队列深度、调度失败 | `queue_names[]`, `time_range`, `filters` |
| 资源碎片 | QueryFragmentation | POST | `/cost-capacity/fragmentation` | 返回碎片率和不可调度资源 | `region_ids[]`, `accelerator_models[]` |
| 容量预测 | QueryCapacityForecast | POST | `/cost-capacity/forecast` | 7d/30d 预测 | `metric_id`, `horizon`, `filters` |

### 12.4.11 指标解释与上下文 API

| 交互行为 | API 名称 | 方法 | 路径 | 功能 | 参数 |
|---|---|---|---|---|---|
| hover 指标名 | GetMetricDefinition | GET | `/metrics/{metric_id}` | 返回定义、单位、公式、相近指标差异 | `metric_id`, `vendor`, `model` |
| 点击“为什么异常” | ExplainMetricAnomaly | POST | `/explain/anomaly` | 返回异常归因候选 | `metric_id`, `resource_ref`, `time_range`, `context_metrics[]` |
| 打开“相近指标差异” | GetMetricRelations | GET | `/metrics/{metric_id}/relations` | 返回相关指标和差异 | `metric_id` |
| 打开采集状态 | GetMetricSourceStatus | GET | `/metrics/{metric_id}/source-status` | 返回 exporter / adapter / stale 状态 | `metric_id`, `filters` |

---

## 12.5 API 请求示例

### 12.5.1 查询汇总趋势

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

### 12.5.2 查询 TopN 低利用卡

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

### 12.5.3 打开单卡详情

```http
GET /api/v1/monitor/resources/accelerators/acc-cn-hz-node01-3?include=current_job,capability,health,source_status
```

响应核心字段：

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

## 13. 权限与多租户

### 13.1 权限模型

| 权限 | 能看到什么 | 不能看到什么 |
|---|---|---|
| Platform Admin | 全部 Region、资源、成本、告警、配置 | 无 |
| SRE | 全部资源健康、告警、Job 技术指标 | 可能隐藏成本金额，只看成本指数 |
| Tenant Admin | 本租户 Job、卡时、成本、效率 | 其他租户 Job 名称和用户信息 |
| User | 自己提交的 Job 和关联资源 | 其他用户任务详情 |
| Viewer | 聚合指标 | 单卡敏感信息、成本、用户信息 |

### 13.2 脱敏规则

| 数据 | 规则 |
|---|---|
| Job 名称 | 非本租户显示 hash 或 alias。 |
| 用户名 | 非授权显示 user hash。 |
| 成本金额 | 无 FinOps 权限显示归一化成本指数。 |
| 节点 hostname | 跨租户可显示 node alias。 |
| 数据集 / Bucket | 只显示 hash，不显示原始路径。 |

---

## 14. 数据质量与异常状态

### 14.1 数据状态

| 状态 | 说明 | UI 表现 |
|---|---|---|
| complete | 所有 Region 数据完整 | 正常展示 |
| partial | 部分 Region 或数据源缺失 | Card 右上角 `Partial` badge |
| stale | 数据超过 freshness SLA | 灰色遮罩 + stale 时间 |
| empty | 无数据 | 空状态，引导修改过滤或检查采集 |
| unsupported | 当前卡型不支持该指标 | 显示 `Not supported by this adapter` |

### 14.2 Freshness SLA

| 指标优先级 | 预期新鲜度 | 超时表现 |
|---|---:|---|
| P0 | <= 5s | 红色 `stale`，告警 |
| P1 | <= 30s | 橙色 `stale` |
| P2 | <= 5min | 灰色提示 |
| P3 | <= 1h | 仅设置页提示 |

---

## 15. 告警策略

### 15.1 阈值类型

| 类型 | 示例 | 使用场景 |
|---|---|---|
| 固定阈值 | 温度 > 85°C | 硬件健康 |
| 事件触发 | Xid errors increase > 0 | 硬件错误 |
| 基线偏离 | Step time > 历史同任务 P95 × 1.2 | 性能退化 |
| 同比/环比 | Tokens/s 比昨日同时间下降 20% | 运营趋势 |
| 组合条件 | 高显存 + 低计算 + 高数据等待 | 归因告警 |
| SLO | 队列 P95 > 30min | 平台服务质量 |

### 15.2 告警降噪

| 机制 | 说明 |
|---|---|
| 去重 | 相同 resource + rule 聚合。 |
| 抑制 | 单卡离线时抑制同卡低利用、温度缺失等衍生告警。 |
| 合并 | 同一 Node 多卡异常合并为 Node-level incident。 |
| 维护窗口 | 标记维护后静默非关键告警。 |
| 自动恢复 | 指标恢复并持续一段时间后 resolved。 |
| 复发识别 | 24h 内同一资源同一规则复发标记 `recurring`。 |

---

## 16. 性能、容量与工程约束

### 16.1 时序存储保留策略

| 数据 | 分辨率 | 保留期 | 用途 |
|---|---:|---:|---|
| Raw P0 | 1s~5s | 6h~24h | 实时排障 |
| Standard | 15s | 7d | 日常趋势 |
| Rollup 1m | 1m | 90d | 运营分析 |
| Rollup 5m | 5m | 180d | 容量规划 |
| Rollup 1h | 1h | 2y | 成本和趋势报表 |
| Events | event | 2y | 告警、审计、复盘 |

### 16.2 基数控制

| 风险 | 控制方式 |
|---|---|
| Job 名称、Pod 名称高基数 | 只把 ID/hash 作为 label，名称放 metadata。 |
| Profiler 算子名高基数 | 不进核心 TSDB，进入 profile store。 |
| 用户自定义 tag 无限制 | allowlist，最多 10 个可索引 tag。 |
| Region 聚合查询过慢 | 预计算常用 rollup 和 TopN。 |
| 指标过多影响 UI | L0/L1/L2 分层，专家模式默认关闭。 |

### 16.3 查询性能目标

| 查询类型 | P95 目标 |
|---|---:|
| Overview 首屏 | < 1.5s |
| 资源表分页 | < 1.2s |
| 单卡详情 | < 800ms |
| 6h 趋势 | < 1.5s |
| 7d rollup 趋势 | < 2.5s |
| TopN | < 2s |
| Job Step 拆解 | < 2.5s |

---

## 17. 产品迭代路线

### 17.1 MVP：4~6 周

| 范围 | 功能 |
|---|---|
| 数据 | NVIDIA DCGM、K8s、基础 Job Hook、基础 PPU Adapter |
| 页面 | Overview、Resources、Alerts |
| 指标 | L0 + 部分 L1：健康、利用、显存、温度、功耗、错误、K8s 状态 |
| 过滤 | Region、Cluster、卡型、Node、Job、健康状态、指标阈值 |
| 聚合 | avg/max/min/sum/topN/basic trend |
| API | bootstrap、meta、summary、resource query、range query、alert search |

### 17.2 V1：8~10 周

| 范围 | 功能 |
|---|---|
| 数据 | NCCL、DataLoader、Checkpoint、Cost、Queue |
| 页面 | Jobs、Trends、Cost & Capacity |
| 指标 | 完整 L1 |
| 交互 | Trend explorer、Brush、Compare、Detail Drawer 完整化 |
| 告警 | 组合规则、静默、复发识别、规则测试 |

### 17.3 V2：12 周+

| 范围 | 功能 |
|---|---|
| 数据 | Profiler/eBPF/专家指标、更多芯片 Adapter |
| 页面 | Expert Mode、Topology、Capacity Forecast |
| 智能分析 | 异常归因、自动推荐过滤、相似 Job 对比 |
| 运营 | SLO、预算、扩容建议、自动维护流程 |

---

## 18. 多轮审查与优化结论

### 18.1 丰富度 vs 简洁性

| 审查点 | 风险 | 决策 |
|---|---|---|
| 指标体系很大 | 首页塞满指标，用户无法判断重点 | 首页只放 12 个 L0 指标，其余进入下钻页和专家模式。 |
| 不同角色需求差异大 | 一个页面无法满足所有人 | SPA 多 Tab，但保持同一过滤栏和同一详情 Drawer。 |
| 专家指标有价值 | 采集开销大、UI 复杂 | Expert Profile 按 Job/时间窗口启用，不默认全量。 |

### 18.2 逻辑性与层次感

| 审查点 | 决策 |
|---|---|
| 页面间关系 | Overview 是入口；Resources 解释硬件和系统；Jobs 解释训练效率；Trends 做比较；Alerts 闭环；Cost 做运营。 |
| 指标递进 | 健康 → 利用 → 瓶颈 → 成本 → 趋势 → 行动。 |
| Card 关系 | KPI Card 给结论，矩阵定位维度，TopN 定位对象，Drawer 给上下文。 |

### 18.3 交互可理解性

| 审查点 | 决策 |
|---|---|
| 指标定义 | 所有核心指标 hover 或点击均显示定义、单位、来源、相近指标差异。 |
| 过滤复杂 | 提供自然语言摘要和常用预设。 |
| 多卡型口径 | 指标 Tooltip 显示当前卡型支持情况和 adapter 口径。 |
| 趋势图难解释 | 叠加事件、Job 阶段和告警，避免只看曲线。 |

---

## 19. 验收标准

### 19.1 产品验收

| 验收项 | 标准 |
|---|---|
| 多 Region | 任意指标支持按 Region 过滤、group by、汇总、趋势。 |
| 多卡型 | H200、RTX PRO 5000、PPU 至少可在同一资源表展示，并能显示各自支持/不支持的指标。 |
| 维度过滤 | Region、Cluster、Node、卡型、Job、租户、用户、健康状态、框架、并行策略可组合。 |
| 指标值过滤 | 支持 `>`, `<`, `between`, `increase`, `rate`, `baseline deviation`, `topN`。 |
| 汇总分析 | 支持 sum、avg、weighted avg、max、min、p95/p99、TopN、分布。 |
| 趋势分析 | 支持单卡趋势和按任意维度聚合趋势。 |
| UI | 符合 Notion 风格 token、SPA、多 Tab、多 Card、Tooltip、Drawer。 |
| API | 每个后端交互行为有明确 API、方法和参数。 |
| 数据质量 | partial/stale/unsupported 状态能在 UI 明确表达。 |

### 19.2 技术验收

| 验收项 | 标准 |
|---|---|
| 首屏性能 | P95 < 1.5s。 |
| 查询性能 | 6h 趋势 P95 < 1.5s，7d rollup P95 < 2.5s。 |
| 数据新鲜度 | P0 <= 5s，P1 <= 30s。 |
| 权限隔离 | 租户不可查看未授权 Job、用户和成本。 |
| 指标治理 | 所有指标必须在指标字典中注册，未注册不展示。 |
| Adapter 能力 | 每个卡型返回 supported/missing/estimated 指标列表。 |

---

## 20. 附录：核心 API 汇总

| API | 方法 | 路径 |
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

## 21. 附录：参考资料映射

| 资料 | 在本设计中的作用 |
|---|---|
| AI 算力监控平台指标分类体系 | 指标层级、采集粒度、频率、聚合、告警策略、P0~P3 优先级。 |
| Notion design analysis | UI 色彩、排版、圆角、Card、Tab、按钮、响应式和视觉约束。 |
| NVIDIA DCGM / DCGM Exporter | NVIDIA GPU 采集和 Prometheus 暴露方式。 |
| NVIDIA DCGM Field IDs | 指标字典 raw field 映射。 |
| Kubernetes Resource Metrics Pipeline | Node/Pod/Container 资源指标来源。 |
| Prometheus Query Functions | 时间窗口聚合、TopN、rate/increase 查询设计。 |
| Thanos / Mimir / OpenTelemetry | 多 Region 指标统一查询和统一数据模型。 |
| NVIDIA H200 / RTX PRO 5000 official specs | 卡型能力元数据。 |
| 阿里云真武 PPU / PAI-PPU 文档 | PPU 适配、PAI/ACS 使用方式和卡型元数据。 |
| NCCL / PyTorch Profiler | 分布式通信和训练性能专家分析。 |
