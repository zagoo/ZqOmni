# ARCHITECTURE.md

## Role
You are an expert Senior Full-Stack Engineer and Architect specializing in high-performance Single Page Applications (SPA).

## Task
Generate code, resolve issues, and extend features for our project strictly adhered to the designated tech stack and architectural constraints outlined below. Do not deviate or introduce unapproved third-party dependencies.

---

## 1. Core Tech Stack & Architectural Vision
This project is built as a highly cohesive, loosely coupled Single Page Application (SPA). All code generation, modifications, and refactoring tasks must strictly adhere to the following tech stack. Alternative third-party libraries are strictly prohibited unless explicitly requested:

*   **Core Framework**: Vue 3 (Composition API with `<script setup>` syntax)
*   **Build Tool**: Vite
*   **Routing**: Vue Router (Centralized setup with module-based auto-aggregation)
*   **State Management**: Pinia (Decentralized, independent stores; Setup-store pattern)
*   **Network Requests**: Axios (Base configuration wrapper + domain-isolated APIs)

### 🧱 Component Building Principles
*   **Logic Separation**: UI rendering must be decoupled from business logic. Complex state and methods must be extracted into composable functions (Hooks) inside `hooks/` directories.
*   **High Cohesion, Low Coupling**: Components must remain highly independent. Use standard `props` and `emits` for communication. Avoid implicit cross-module dependencies.

---

## 2. 🛑 Strict Architectural & Tech Stack Constraints

### 2.1 Backend Database
- PostgreSQL (Latest stable version).
- All migrations must use **Alembic**. No raw SQL or manual schema updates.

### 2.2 Backend API Framework
- **FastAPI** leveraging Python's `async/await` throughout the entire data flow.
- **SQLAlchemy 2.0+** as the ORM, utilizing the modern `Mapped[...]` and `mapped_column()` type-annotated declarations. Do not use deprecated v1.x syntaxes.
- Use `AsyncSession` for all database interactions.

### 2.3 API Response Standardization
- All responses must be wrapped globally in a generic Pydantic schema containing:
  `code: int` (business status code), `message: str`, and `data: Optional[T] = None`.
- Properly handle pagination via a specialized nested Pydantic generic model.

### 2.4 Frontend Architecture
- **Vue 3** (Composition API with `<script setup>` syntax) + **TypeScript**.
- Build Tool: **Vite** with strict configuration of reverse proxy (`/api`) to eliminate CORS issues during development.

### 2.5 API Client & Type Generation (SSOT)
- Front-end must NEVER write raw HTTP fetch/axios requests or duplicate TypeScript interfaces manually.
- Generate all frontend clients and TypeScript interfaces automatically from FastAPI's `/openapi.json` using `@hey-api/openapi-ts`.

### 2.6 Authentication & Security
- Stateless **JWT-based authentication** using a Dual-Token system (Short-lived `Access Token` passed in HTTP header, long-lived `Refresh Token`).
- Implement a silent, seamless token refresh mechanism via frontend interceptors to prevent user interruption upon Access Token expiration.

### 2.7 Advanced Form & Chart Extensions
- Leverage **VueUse** composables for all reactive window/element handling, debouncing, and v-model bindings.
- Use **vue-echarts** (with granular tree-shaking/on-demand imports of ECharts modules) for all data visualizations.

---

## 3. Directory Layout Constraints
When creating new files, pages, or modules, the AI must strictly follow this directory topology:

```text
my-industrial-spa/
├── docker-compose.yml         # [§5] Orchestrates PostgreSQL, FastAPI, and Vue 3 containers
├── CLAUDE.md                  # Development command guide and runtime instructions for AI
├── architecture.md            # [Prompt 1] Strict technical stack and architecture guardrails
│
├── backend/                   # ======= BACKEND (PYTHON FASTAPI) =======
│   ├── Dockerfile             # Development container environment build file
│   ├── requirements.txt       # Dependencies (fastapi, sqlalchemy, alembic, pydantic, pyjwt, etc.)
│   ├── alembic.ini            # [§2.1] Alembic database migration configuration
│   ├── alembic/               # [§2.1] Automatically generated database migration scripts
│   │   ├── env.py
│   │   └── versions/          # Version history files tracking database schema modifications
│   └── app/
│       ├── main.py            # FastAPI entrypoint, mounts CORS/middlewares, exports openapi.json
│       ├── core/              # Core foundational components
│       │   ├── config.py      # App settings mapping environment variables
│       │   └── security.py    # [§2.6] JWT payload encoding/decoding and password hashing
│       ├── database.py        # [§2.2] SQLAlchemy AsyncEngine and AsyncSession lifecycle factory
│       ├── models/            # [§2.2] Database ORM persistent models using Modern Mapped syntax
│       │   ├── base.py        # Shared SQLAlchemy DeclarativeBase instance
│       │   └── user.py
│       ├── schemas/           # [§2.3] Data validation and payload contracts via Pydantic
│       │   ├── response.py    # [§2.3] Standardized generic structures (ApiResponse[T], PageData[T])
│       │   └── user.py
│       └── routers/           # API endpoint routing layers split by domain boundaries
│           ├── auth.py        # [§2.6] Authentication routes (Login and Dual-Token refresh endpoint)
│           └── users.py
│
└── frontend/                  # ======= FRONTEND (VUE 3 SPA) =======
    ├── Dockerfile             # Frontend local Vite development container configuration
    ├── package.json           # Package definitions (vue, pinia, @vueuse/core, vue-echarts, etc.)
    ├── tsconfig.json          # Strict TypeScript engine parameters compilation overrides
    ├── vite.config.ts         # [§2.4] Bundler config with reverse proxy mapped for `/api`
    ├── index.html             # Single Page Application HTML mount container entrypoint
    └── src/
        ├── main.ts            # Frontend entrypoint, wires Pinia and intercepts SDK engine hooks
        ├── App.vue            # Root presentation viewport — contains the single `<AppShell>`
        ├── assets/            # Global static assets (common styles, global images, base icons)
        ├── components/        # 🏢 Global base UI components (pure presentational, no business logic)
        ├── composables/       # ⚓ Global common hooks (e.g., useAuth, useTheme)
        ├── router/            # 🛣️ Routing hub
        │   ├── index.ts       # Main router entry (auto-scans and aggregates 'modules/' via import.meta.glob)
        │   └── modules/       # Route segmentations per business domain
        ├── store/             # 🏪 Global Pinia state hub (Setup-store pattern)
        │   ├── index.ts       # Pinia initialization entry
        │   ├── shell.ts       # Global app-shell UI state
        │   └── auth.ts        # Manages access token and coordinates non-disruptive refresh flows
        ├── api/
        │   └── generated/     # [§2.5] 100% generated by openapi-ts. DO NOT MANUALLY MODIFY.
        │       ├── services.ts# Automatically mapped asynchronous wrapper functions for endpoints
        │       ├── types.ts   # Extracted TypeScript models derived natively from Pydantic schemas
        │       └── client.ts  # Core HTTP client instance where global JWT interceptors are mounted
        └── views/             # 📦 Core isolation zone for business modules (Domain-driven Views)
            └── [module_name]/ # Target functional business module (e.g., user, order)
                ├── api/       # 🔌 Re-exports of generated services consumed by this module
                │   └── index.ts
                ├── components/# 🧩 Private components exclusive to this module
                ├── hooks/     # ⚓ Private business logic hooks exclusive to this module
                ├── store/     # 🏪 [Optional] Module-specific Pinia stores
                └── [Page].vue # 📄 Module view pages
```

---

## 4. Progressive Development & "Zero-Interference" Safeguards
To guarantee that newly added features never break or interfere with existing production modules, the AI must implement the following isolation strategies:

### 🔌 4.1 Interface Isolation: Module-Based API Management
*   **Global Foundation**: Global JWT interceptors and unified error handling are mounted on the generated client at `src/api/generated/client.ts`. A hand-written `src/utils/request.ts` is forbidden (per §2.5).
*   **Local Autonomy**: Creating a massive, unified global `api.ts` file is strictly forbidden. Each business module's `views/[module_name]/api/index.ts` re-exports only the subset of generated functions and TypeScript types it consumes from `src/api/generated/`. Hand-rolled fetch/axios calls inside modules are forbidden.
*   **Dependency Direction**: Pages can only import APIs from their own module's `api/index.ts` or explicitly designated global shared services.

### 🛣️ 4.2 Routing Isolation: Dynamic Module Registration
*   `src/router/index.ts` must use Vite's `import.meta.glob` to automatically scan and register route configurations from the `modules/` directory.
*   **Adding Features**: To add a new domain, create a new `[module_name].ts` file inside `src/router/modules/`. **Modifying the main router file (`index.ts`) directly is prohibited**.

### 🧩 4.3 Component & State Isolation
*   **The Locality Principle**: Do not lift a component or a Pinia store to global directories (`src/components/` or `src/store/modules/`) unless it is explicitly confirmed to be reused across at least **3 separate** business modules.
*   **Destruction Safety**: The system architecture must guarantee that running `rm -rf src/views/[module_name]` along with removing its respective route file allows the project to compile with zero errors and leave no trace of dead code.

---

## 5. Development Workflow & DevOps
- The entire stack (Vue 3 dev server + FastAPI hot-reload + PostgreSQL 15+) must be orchestrated via a single **Docker Compose** file (`docker-compose.yml`) ensuring instant local environment setup.

---

## 6. AI Execution Constraints
When a code generation or modification prompt is received, the AI must execute the following self-check sequence:
1.  **Identify Boundaries**: Determine which specific `[module_name]` the task belongs to. If it is a completely new feature, scaffold a new directory under `views/`.
2.  **Protect Global Scope**: Unless explicitly commanded to refactor, do not modify files in `src/components/`, other unrelated business modules, or global utility files.
3.  **Code Style Consistency**: Always use TypeScript with `<script setup lang="ts">` syntax. Ensure strong typing for Axios response schemas and component Props.

---

## 7. 💡 Output Expectation
When writing or reviewing code, always enforce type safety, use async best practices on the backend, ensure proper reactivity on the frontend, and verify that the data schemas align perfectly across the network boundaries.
