## Target
Build a data and AI infrastructure platform for Physical AI computing

## Platform Positioning Statement
A one-stop data and compute infrastructure platform for the humanoid robotics Physical AI domain. Built on a "data-and-model dual-wheel closed-loop" architecture, its core mission is to drive the efficient, streaming, and deterministic transformation of raw physical process recordings into structured, high-value, model-learnable assets, thereby enabling high-dynamic, full-chain Sim-to-Real evolution.

## Functional Architecture: The Four Logical Subsystems

### 1. Multi-Modal Physical Data Factory & Loop
Focuses on the ingestion, cleaning, spatio-temporal alignment, and assetization of multi-source, heterogeneous data from the real world.

* Real-World Streaming Data Acquisition: Supports ultra-high frequency, massive throughput ingestion of multi-source sensor data (LiDAR, Cameras, IMUs, tactile sensors, CAN bus). Built to handle high-concurrency, low-latency edge-to-cloud flash streaming challenges.
* Multi-Modal Physical Data Lake: Provides a unified storage foundation optimized for 4D (spatio-temporal) sensor fusion. It natively supports raw multi-modal files such as point clouds, raw video streams, and robotic control sequences with highly parallelized read/write operations.
* Spatio-Temporal Data Pipeline: Resolves the critical pain points of sensor clock drifts and spatial coordinate mismatches. Achieves microsecond-level cascading alignment across asynchronous sensor streams while executing automated data cleaning, standardization, and structured organization.
* Foundation Model-Driven Auto-Annotation: Leverages cutting-edge Vision-Language-Model (VLM) and Vision-Language-Action (VLA) capabilities to automate long-video event chunking, fine-grained atomic action semantic labeling, spatial bounding box grounding, and cross-modal natural language caption generation, significantly slashing data labeling costs.
* Human-in-the-Loop Annotation & QA: Equips engineers with high-performance 3D/4D hybrid interactive canvas annotation tools. Integrates multi-tiered data validation algorithms to filter out edge cases and high-value samples via active learning mechanisms, ensuring absolute data reliability.
* Physical Asset Data Governance & Mining: Establishes rigorous data lineage, lineage mapping, and privacy compliance tracking for physical assets. Features a multi-dimensional search and mining engine driven by "semantic + spatial + action" feature vectors to rapidly pinpoint and harvest rare edge-case scenarios for model retraining.

### 2. Dual-Driven Twin Data Generation & Simulation
Focuses on shattering the physical boundaries of data scarcity by using Generative AI and physics simulation to construct a boundless training playground.

* Physics-Aware Simulation Platform: Deeply integrates high-throughput physics engines (such as [NVIDIA Omniverse/Isaac Lab](https://www.therobotreport.com/nvidia-releases-new-updated-tools-physical-ai-gtc-taipei-computex/) blueprint architectures) to provide photorealistic and structurally accurate digital twin environments [3]. Enables low-cost, massively parallelized Reinforcement Learning (RL) policy training and rapid iteration.
* Physics-Based Data Augmentation: Deploys domain randomization algorithms governed by real-world physical laws to inject photorealistic variations (lighting shifts, weather variations, sensor noise, dynamic physical obstacles) into real-world data, drastically increasing model generalization.
* Generative Data Synthesis: Combines 3D Gaussian Splatting (3DGS), Neural Radiance Fields (NeRF), and World Models to achieve end-to-end photorealistic 3D scene reconstruction and synthetic data generation for rare or dangerous edge cases (e.g., traffic accidents, sudden mechanical failures).
* Physical Data Value Closed-Loop: Connects "acquisition, mining, simulation, synthesis, and retraining" into a continuous flywheel. This ensuring that raw, chaotic physical process logs captured by hardware are continuously distilled, refined, and converted into valuable model-learnable structured assets.

### 3. Closed-Loop Model Ops (VLA ModelOps)
Focuses on agile training, multi-dimensional capability evaluation, and edge-deployment optimization of Perception-Action foundation models.

* Multi-Modal/Spatio-Temporal Model Training: Supports distributed, highly parallelized training of embodied/generic physical foundation models across perception, temporal control, 3D spatial reasoning, and action prediction domains.
* Agile Experiment Management: Tracks the complete lineage of the training lifecycle, including hyperparameters, code versions, dataset snapshot dependencies, and weights checkpoints, guaranteeing full auditability and reproducibility of complex Physical AI training jobs.
* Comprehensive Model Evaluation Framework: Moves beyond traditional digital metrics (e.g., Loss, Accuracy) to build a multi-dimensional physical world evaluation matrix. This metrics system quantifies perception accuracy, temporal continuity, 3D spatial collision avoidance rates, and long-horizon action prediction stability.
* Hardware-Aware Compilation & Artifacts Management: Optimizes models for heterogeneous edge silicon (e.g., vehicle boards, robotic computing units, edge NPUs/TPUs) through hardware-aware quantization (INT8/FP4/FP8), pruning, and compilation. Manages strict deployment packages and versioning for secure Over-The-Air (OTA) firmware delivery.

### 4. Full-Pipeline Task Orchestration & Compute Infrastructure
The robust backbone of the platform, providing ultimate performance guarantees, multi-tenancy, and deterministic execution.

* End-to-End Task Orchestration: Features a Directed Acyclic Graph (DAG) workflow orchestration engine that coordinates the entire data-to-model pipeline—from data ingestion, auto-labeling, and simulation rendering, to distributed training and virtual closed-loop evaluation.
* Compute Resource Management, Scheduling & Monitoring: Dynamically provisions and manages heterogeneous resource pools (CPUs, GPUs, dedicated simulation clusters). Supports topology-aware scheduling and multi-tenant hard slicing for large-scale compute clusters. Delivers real-time alerting for cluster health, throughput, and Out-Of-Memory (OOM) redlines.
* Multi-Modal 4D Spatio-Temporal Studio: Built upon an immersive 4D spatial canvas (e.g., similar to [Rerun/Foxglove architectures](https://rerun.io/blog/physical-ai-data)), seamlessly synchronizing 3D perception bounding boxes, kinematics topology, joint torques, and sequential action tokens with real-time video streams along a single unified timeline [3]. This studio enables researchers to scrub through frames at any speed, visualize step-by-step token execution, and intuitively understand exactly what the model "saw, thought, and executed" in the physical world.
