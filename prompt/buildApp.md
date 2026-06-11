## Task
Build a data and AI infrastructure platform for Physical AI computing

## Input
The **Functional Design Document**: @FDD.md

## Constraint
You MUST strictly adhere to `FDD.md` as the single source of truth.

**Scope Lock — Absolute Constraint:**
Implement ONLY the following three modules in full, exactly as specified in FDD.md. All other platform capabilities MUST remain as zero-implementation stubs.

**Fully Implement:**
- **M01** — Platform Login & Session Management
- **M02** — Tenant & Resource Management
- **M03** — User, Role & Permission Management

**Zero-Implementation Rule for Everything Else:**
- For any feature, page, API endpoint, or module NOT listed above, you MUST ONLY create:
  - A **UI navigation entry / menu item** (placeholder route and empty page shell).
  - An **API route stub** returning `501 Not Implemented` or equivalent.
  - **NO business logic, NO database schema, NO service implementation, NO frontend components** beyond the minimal shell.
- Do NOT write TODO comments promising future implementation.
- Do NOT add speculative code, abstractions, or data models for out-of-scope features.

**Enforcement:**
- Before writing any code, verify the file or function belongs to M01, M02, or M03.
- If in doubt, treat it as out-of-scope and apply the Zero-Implementation Rule.
- All implemented modules must integrate correctly with each other per FDD.md (e.g., M03 permissions must guard M02 resources; M01 sessions must propagate tenant context).

Output production-ready, type-safe, well-tested code for the three in-scope modules only.
