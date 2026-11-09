# HUCE-KMS — Technical Naming Standards & Identifier Conventions

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: Technical Naming Standards & Identifier Conventions  
> **Scope**: All engineers and AI Coding Agents developing in `apps/backend`  
> **Last Updated**: 2026-11-08  

This document standardizes technical naming conventions across the HUCE-KMS backend codebase, highlights existing patterns, and specifies naming rules for new modules.

---

## 1. Naming Standards Overview

| Component | Format Convention | Status | Existing Codebase Example | Rule for New Modules |
| :--- | :--- | :--- | :--- | :--- |
| **Directory / Package** | `snake_case` | Verified | `api/core`, `api/models`, `api/repositories` | `api/documents`, `api/categories` |
| **Python Files / Modules** | `snake_case.py` | Verified | `config.py`, `database.py`, `refresh_token.py` | `document.py`, `chat_session.py` |
| **General Classes** | `PascalCase` | Verified | `Settings`, `PaginationParams`, `AppException` | `DocumentParser`, `EmbeddingGenerator` |
| **SQLAlchemy ORM Models** | `PascalCase` (Singular) | Verified | `User`, `RefreshToken` | `Document`, `Category`, `Conversation` |
| **Database Tables** | `snake_case` (Plural) | Verified | `users`, `refresh_tokens` | `documents`, `categories`, `messages` |
| **Database Columns / Fields** | `snake_case` | Verified | `id`, `user_id`, `hashed_password`, `is_active` | `category_id`, `file_path`, `is_published` |
| **Foreign Key Columns** | `<singular_table>_id` | Verified | `user_id` (references `users.id`) | `document_id`, `category_id` |
| **Pydantic Schemas** | `PascalCase` + Suffix | Verified | `UserBase`, `UserCreate`, `UserResponse`, `UserUpdate` | `DocumentCreate`, `DocumentResponse` |
| **Repository Classes** | `PascalCase` + `Repository` | Verified | `BaseRepository`, `UserRepository`, `RefreshTokenRepository` | `DocumentRepository`, `CategoryRepository` |
| **Service Classes** | `PascalCase` + `Service` | Verified | `AuthService`, `UserService` | `DocumentService`, `SearchService` |
| **Route Modules** | `snake_case.py` | Verified | `auth.py`, `users.py`, `router.py` | Plural resource names: `documents.py` |
| **REST API Endpoints** | `kebab-case` / lowercase | Verified | `/api/v1/auth/change-password`, `/api/v1/users/{user_id}` | `/api/v1/documents/upload` |
| **FastAPI Dependency Aliases**| `PascalCase` + `Dep` | Verified | `DatabaseDep`, `CurrentUserDep`, `AdminUserDep`, `UserServiceDep` | `DocumentServiceDep`, `CategoryServiceDep` |
| **Functions & Methods** | `snake_case` | Verified | `get_by_username`, `create_user_by_admin`, `revoke_all_for_user` | `process_document`, `extract_text` |
| **Variables & Attributes** | `snake_case` | Verified | `access_token`, `current_user`, `is_healthy` | `document_id`, `total_chunks` |
| **Constants** | `UPPER_SNAKE_CASE` | Verified | `BACKEND_DIR`, `DATABASE_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES` | `MAX_FILE_SIZE_BYTES`, `ALLOWED_EXTENSIONS` |
| **Type Aliases & TypeVars** | `PascalCase` | Verified | `DataType`, `ModelType`, `UserRole` | `DocumentStatus`, `QueryFilter` |
| **Enum Members** | `UPPER_SNAKE_CASE` | Recommendation | Currently string literals `"user"`, `"admin"` | `USER = "user"`, `ADMIN = "admin"` |
| **Test Files (Future)** | `test_<module>.py` | Recommendation | No tests currently exist | `test_auth.py`, `test_users.py` |
| **Test Functions (Future)** | `test_<action>_<expected>` | Recommendation | No tests currently exist | `test_login_success()`, `test_login_invalid_password()` |

---

## 2. Detailed Conventions by Component

### 2.1. File & Module Naming
- File names MUST be lowercase with underscore separators (`snake_case.py`):
  - Model: `user.py`, `refresh_token.py` (singular noun describing the entity).
  - Schema: `user.py`, `common.py` (matching the domain).
  - Repository: `user.py`, `refresh_token.py` (matching the entity managed).
  - Service: `auth.py`, `user.py` (matching the feature or entity).
  - Route: `auth.py`, `users.py` (collection of route endpoints).

### 2.2. Class Naming
- Use **`PascalCase`** for all class declarations.
- Suffix rules by architectural layer:
  - Repository: `<Entity>Repository` (e.g., `UserRepository`, `RefreshTokenRepository`).
  - Service: `<Feature/Entity>Service` (e.g., `AuthService`, `UserService`).
  - ORM Model: Singular noun without suffix (e.g., `User`, `RefreshToken`).
  - Exception: `<Reason>Exception` (e.g., `AppException`, `ConflictException`, `EntityNotFoundException`).

### 2.3. Pydantic Schemas Naming
To distinguish schema roles, the codebase applies standardized prefixes and suffixes:
- `<Entity>Base`: Shared base schema with common attributes (e.g., `UserBase`).
- `<Entity>Create`: Public registration or creation payload (e.g., `UserCreate`).
- `Admin<Entity>Create`: Privileged creation payload with administrative controls (e.g., `AdminUserCreate`).
- `<Entity>Update`: General update payload (e.g., `UserUpdate`).
- `<Entity><Field>Update`: Dedicated single-attribute update payload (e.g., `UserStatusUpdate`, `UserRoleUpdate`).
- `<Entity>Response`: Outgoing schema representing an entity returned to clients (e.g., `UserResponse`).
- `<Action>Request`: Payload for RPC-style non-CRUD operations (e.g., `ChangePasswordRequest`).
- `<Entity>Login` / `<Entity>Logout`: Authentication schemas (e.g., `UserLogin`).

### 2.4. Functions & Methods Naming
Function and method names MUST start with an **action verb**:
- **Single Record Queries**: `get_by_<field>` (e.g., `get_by_id`, `get_by_username`, `get_by_email`, `get_by_token`).
- **List Queries**: `list` or `list_<entities>` (e.g., `list()`, `list_users()`).
- **Paginated Search with Count**: `search_with_count(...)`.
- **Creation**: `create` or `create_<entity>_by_<actor>` (e.g., `create()`, `create_user_by_admin()`).
- **Updates**: `update` or `update_<entity>_<field>` (e.g., `update()`, `update_user_status()`).
- **Deletion & Revocation**: `delete` or `revoke` (e.g., `delete()`, `revoke()`, `revoke_all_for_user()`).
- **FastAPI Dependencies**: Prefixed with `get_` (e.g., `get_db_session`, `get_current_user`, `get_pagination_params`, `get_user_service`).

### 2.5. API Endpoints & Routes Naming
- Root API prefix: `/api/v1` (configured via `settings.API_V1_PREFIX`).
- Entity collections: Lowercase plural nouns: `/api/v1/users`.
- Operations on specific entities: Using path parameter `{id}`:
  - Retrieve details: `GET /api/v1/users/{user_id}`
  - Partial profile update: `PATCH /api/v1/users/{user_id}`
  - Status update: `PATCH /api/v1/users/{user_id}/status`
  - Role update: `PATCH /api/v1/users/{user_id}/role`
- RPC-style authentication and stateful operations: Functional nouns or compound verbs formatted in `kebab-case`:
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/refresh`
  - `POST /api/v1/auth/logout`
  - `POST /api/v1/auth/change-password`
  - `GET /api/v1/auth/me`

### 2.6. Database Tables & Columns Naming
- **Table Names**: Always lowercase plural nouns with underscores (`snake_case`):
  - `users`
  - `refresh_tokens`
- **Primary Key**: Always named `id` (autoincrementing integer, primary key).
- **Foreign Keys**: Named as `<singular_table>_id` (e.g., `user_id` referencing `users.id`).
- **Boolean / Status Columns**: Prefixed with `is_` or `has_`:
  - `is_active`
  - `is_revoked`
- **Timestamp Columns**: Suffixed with `_at`:
  - `created_at`
  - `updated_at`
  - `expires_at`

---

## 3. Existing Observations & Standardization Guidelines

### 3.1. Route Module Naming & URL Prefixes (Singular vs. Plural)
- **Current Observation**:
  - `auth.py` uses prefix `/auth` (functional noun / action domain), Swagger Tag: `["Authentication"]`.
  - `users.py` uses prefix `/users` (plural collection for REST entity), Swagger Tag: `["Users"]`.
- **Recommendation for New Modules**:
  - Entity/CRUD collections **MUST** use plural nouns (e.g., `/documents`, `/categories`).
  - Action/Utility modules MAY use functional nouns (e.g., `/auth`, `/chat`, `/search`).

### 3.2. Role Definitions: Literal vs. Model Column
- **Current Observation**:
  - In `api/schemas/user.py`, user roles are typed via `UserRole = Literal["user", "admin"]`.
  - In `api/models/user.py`, the role column is declared as `String(20)` with default `"user"`, documented via comments.
- **Future Recommendation**:
  - Maintain the current pattern during Phase 1 (no breaking changes).
  - In future PostgreSQL migrations, consider introducing a shared Python `StrEnum` (`class UserRole(StrEnum): USER = "user"; ADMIN = "admin"`).

### 3.3. Pagination: `skip`/`limit` in Queries vs. `page`/`total_pages` in Schemas
- **Current Observation**:
  - Query parameters accept `skip` and `limit` (`PaginationParams`).
  - Response metadata calculates `page` (1-based) and `total_pages` (`PaginationMeta`).
- **Recommendation**:
  - This pattern is standard and client-friendly. New modules MUST continue this pattern: receive `skip`/`limit` via `PaginationDep` and construct response envelopes using `PaginationMeta.create(total=total, skip=skip, limit=limit)`.
