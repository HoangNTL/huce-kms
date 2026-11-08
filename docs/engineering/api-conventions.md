# HUCE-KMS — API Engineering Standards & Conventions

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: API Engineering Standards & Endpoint Design Rules  
> **Scope**: All Route Handlers and Controllers in `apps/backend/src/api/v1/routes`  
> **Last Updated**: 2026-11-08  
> **Rule Prefix**: `API-xxx`

---

## 1. API Layer Architecture Overview

The API layer (located at `apps/backend/src/api/v1/routes/`) acts as the HTTP interface boundary between external clients (Next.js frontend, third-party integrations) and internal services.

Every route handler in HUCE-KMS is exclusively responsible for:
1. Receiving HTTP requests and deserializing parameters (query, path, headers, cookies, body) into Pydantic DTOs.
2. Authenticating user identity and verifying permissions via dependencies (`CurrentUserDep`, `AdminUserDep`).
3. Instantiating and invoking the corresponding domain service via factory dependencies (`UserServiceDep`, `AuthServiceDep`).
4. Setting session cookies where applicable (`Set-Cookie: refresh_token=...`).
5. Wrapping outgoing data into the standard `BaseResponse[DataType]` response envelope.

**Strict Architectural Boundary**: Route handlers **MUST NOT** execute raw SQL or ORM queries, interact directly with Repositories, or contain complex domain business logic.

---

## 2. API Design Rules Catalog

### Rule ID: API-001
**Title:** URL Prefix and API Versioning  
**Priority:** MUST  
**Rule:** All domain endpoints **MUST** be placed under the `/api/v1` version prefix (configured centrally via `settings.API_V1_PREFIX`). Sub-module routers **MUST** be aggregated into `api_router` in `api/v1/routes/router.py` before being mounted onto the main FastAPI application in `api/main.py`.  
**Reason:** Ensures backward compatibility when upgrading APIs in future releases without disrupting existing client applications.  
**Correct Example:**
```python
# api/v1/routes/router.py
api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# api/main.py
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
```
**Incorrect Example:**
```python
# Mounted directly to app without version prefix
app.include_router(users.router, prefix="/users")
```
**Exceptions:** Infrastructure monitoring and documentation endpoints: `/health`, `/docs`, `/redoc`, `/openapi.json`, `/`.  
**Source:** `apps/backend/src/api/main.py`, `apps/backend/src/api/v1/routes/router.py`.

---

### Rule ID: API-002
**Title:** Resource and Endpoint Naming Conventions  
**Priority:** MUST  
**Rule:** 
- Entity collection paths (CRUD resources) **MUST** be lowercase plural nouns (e.g., `/users`, `/documents`, `/categories`).
- Specific resource identifiers **MUST** use path parameters `{id}` or `{<entity>_id}` (e.g., `/users/{user_id}`).
- RPC-style action endpoints **MUST** use functional nouns or compound verbs formatted in `kebab-case` (e.g., `/auth/change-password`, `/users/{user_id}/status`, `/users/{user_id}/role`).
- Endpoint paths **MUST NOT** contain file extensions (e.g., `.json`, `.php`) or underscore characters `_`.  
**Reason:** Enforces international RESTful standards, enabling predictable URL structures and automated client SDK generation.  
**Correct Example:**
```python
# Collection and resource item management
@router.get("/users")
@router.get("/users/{user_id}")
@router.patch("/users/{user_id}/status")

# RPC-style authentication action
@router.post("/auth/change-password")
```
**Incorrect Example:**
```python
@router.get("/get_user_by_id/{id}")       # Contains verb and snake_case
@router.post("/user/create")              # Singular noun with action verb
@router.patch("/users/{user_id}/update_status") # Redundant action verb in path
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/v1/routes/users.py`, `apps/backend/src/api/v1/routes/auth.py`.

---

### Rule ID: API-003
**Title:** Standard HTTP Methods Mapping  
**Priority:** MUST  
**Rule:** Every operation **MUST** align strictly with the standard semantics of HTTP methods:
- `GET`: Retrieve resource data (idempotent, safe, no side-effects on system state).
- `POST`: Create a new resource or execute complex stateful operations (login, logout, refresh, change-password).
- `PATCH`: Partially update resource attributes.
- `PUT`: Completely replace a resource (the platform prefers `PATCH` to avoid accidental attribute overwrites).
- `DELETE`: Remove or deactivate a resource.  
**Reason:** Preserves HTTP protocol standards, supporting network middleware, proxies, and browser caching optimizations.  
**Correct Example:**
```python
@router.get("/{user_id}", summary="Get user details")
@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create user")
@router.patch("/{user_id}", summary="Update user profile")
@router.delete("/{user_id}", summary="Delete user")
```
**Incorrect Example:**
```python
@router.get("/delete-user/{user_id}")  # Uses GET for data deletion
@router.post("/get-user")              # Uses POST for read-only query
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/v1/routes/users.py`.

---

### Rule ID: API-004
**Title:** Standard Response Envelope `BaseResponse[T]`  
**Priority:** MUST  
**Rule:** All functional domain endpoints **MUST** declare `response_model=BaseResponse[DataType]` and return a `BaseResponse` object containing 4 standardized fields: `success` (bool), `code` (string), `message` (string), and `data` (DataType | None). Route handlers **MUST NOT** return bare dictionaries or unencapsulated model instances.  
**Reason:** Guarantees a consistent response envelope for client consumers (Next.js frontend), simplifying generic fetch wrappers and error interceptors.  
**Correct Example:**
```python
@router.get(
    "/{user_id}",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user(user_id: int, service: UserServiceDep):
    user = await service.get_user_by_id(user_id)
    return BaseResponse(
        code="USER_FOUND",
        message="User details retrieved successfully.",
        data=user,
    )
```
**Incorrect Example:**
```python
@router.get("/{user_id}")
async def get_user(user_id: int, service: UserServiceDep):
    user = await service.get_user_by_id(user_id)
    return user  # Returns raw model without BaseResponse envelope
```
**Exceptions:** The `/health` infrastructure probe endpoint returns raw JSON to maintain compatibility with Docker and Kubernetes health checkers.  
**Source:** `apps/backend/src/api/schemas/common.py`, `apps/backend/src/api/v1/routes/users.py`.

---

### Rule ID: API-005
**Title:** Standard Paginated List Envelope `PaginatedData[T]`  
**Priority:** MUST  
**Rule:** Endpoints returning paginated lists **MUST** wrap results in `BaseResponse[PaginatedData[T]]`, where `PaginatedData` encapsulates `items: list[T]` and `pagination: PaginationMeta`.  
**Reason:** Provides standardized pagination metadata (`total`, `skip`, `limit`, `page`, `total_pages`) directly to UI components without requiring client-side calculation.  
**Correct Example:**
```python
@router.get(
    "/",
    response_model=BaseResponse[PaginatedData[UserResponse]],
    status_code=status.HTTP_200_OK,
)
async def list_users(
    pagination: PaginationDep,
    admin_user: AdminUserDep,
    service: UserServiceDep,
):
    data = await service.list_users(skip=pagination.skip, limit=pagination.limit)
    return BaseResponse(
        message="Users list retrieved successfully.",
        data=data,
    )
```
**Incorrect Example:**
```python
@router.get("/")
async def list_users(service: UserServiceDep):
    users = await service.list_all()
    return BaseResponse(data=users)  # Raw array without pagination metadata
```
**Exceptions:** Small static reference collections (under 20 items) without pagination may return `BaseResponse[list[T]]`.  
**Source:** `apps/backend/src/api/schemas/common.py`, `apps/backend/src/api/v1/routes/users.py`.

---

### Rule ID: API-006
**Title:** Standardized Pagination Query Parameters `PaginationDep`  
**Priority:** MUST  
**Rule:** All paginated list endpoints **MUST** receive parameters via the `PaginationDep` dependency (`api/core/dependencies.py`). This dependency enforces:
- `skip`: Integer $\ge 0$, defaulting to `0`.
- `limit`: Integer between `1` and `100`, defaulting to `10`.  
**Reason:** Prevents client requests with excessive `limit` values from consuming server memory (DoS vulnerability) and standardizes query naming across the platform.  
**Correct Example:**
```python
@router.get("/", response_model=BaseResponse[PaginatedData[UserResponse]])
async def list_users(
    pagination: PaginationDep,
    service: UserServiceDep,
):
    ...
```
**Incorrect Example:**
```python
@router.get("/")
async def list_users(
    offset: int = 0,      # Inconsistent parameter naming instead of 'skip'
    page_size: int = 500, # Unconstrained limit exceeding le=100
):
    ...
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/dependencies.py:27-35`.

---

### Rule ID: API-007
**Title:** Standard HTTP Status Codes  
**Priority:** MUST  
**Rule:** Endpoints **MUST** declare and return semantic HTTP status codes using the `fastapi.status` enum:
- `status.HTTP_200_OK`: Successful `GET`, `PATCH`, `PUT`, and non-creational `POST`.
- `status.HTTP_201_CREATED`: Successful resource creation (`POST`).
- `status.HTTP_204_NO_CONTENT`: Successful deletion without response body.
- Endpoints **MUST NOT** return `200 OK` when an operation fails. Errors MUST return HTTP status codes in the 4xx or 5xx ranges.  
**Reason:** Ensures client HTTP interceptors catch failures at the transport layer without parsing response payloads.  
**Correct Example:**
```python
@router.post(
    "/register",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: UserCreate, service: AuthServiceDep):
    ...
```
**Incorrect Example:**
```python
@router.post("/register")  # Missing status_code 201 for resource creation
async def register(payload: UserCreate):
    ...
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/v1/routes/auth.py:51-56`, `apps/backend/src/api/v1/routes/users.py:36-41`.

---

### Rule ID: API-008
**Title:** Route-Level Dependency Injection Factory for Services  
**Priority:** MUST  
**Rule:** Each route module **MUST** define a factory function accepting `db: DatabaseDep` that initializes the corresponding Service and its Repositories, encapsulated via `Annotated[ServiceClass, Depends(factory)]`. Route handlers **MUST NOT** manually instantiate service classes inside function bodies.  
**Reason:** Harnesses FastAPI's dependency injection system, enabling straightforward dependency overriding during integration testing without modifying production code.  
**Correct Example:**
```python
# api/v1/routes/users.py
def get_user_service(db: DatabaseDep) -> UserService:
    user_repo = UserRepository(db)
    refresh_token_repo = RefreshTokenRepository(db)
    return UserService(user_repo, refresh_token_repo)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]

@router.get("/{user_id}")
async def get_user(user_id: int, service: UserServiceDep):
    return await service.get_user_by_id(user_id)
```
**Incorrect Example:**
```python
@router.get("/{user_id}")
async def get_user(user_id: int, db: DatabaseDep):
    # Manual instantiation inside handler breaches DI conventions
    repo = UserRepository(db)
    service = UserService(repo, RefreshTokenRepository(db))
    return await service.get_user_by_id(user_id)
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/v1/routes/users.py:24-30`, `apps/backend/src/api/v1/routes/auth.py:18-24`.

---

### Rule ID: API-009
**Title:** OpenAPI Documentation and Metadata  
**Priority:** SHOULD  
**Rule:** Every endpoint **SHOULD** specify a concise `summary` (under 80 characters), a detailed docstring, and special response headers (such as cookie descriptions for login/refresh) via the `responses` decorator argument.  
**Reason:** Swagger UI (`/docs`) and ReDoc (`/redoc`) serve as the contract for frontend and test engineers. Clear descriptions prevent communication bottlenecks.  
**Correct Example:**
```python
@router.post(
    "/login",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Login: Returns Bearer access token & sets HTTP-only refresh token cookie",
    responses={
        200: {
            "description": "Login successful. Returns access token and sets secure HTTP-only cookie.",
        }
    },
)
async def login(...):
    """Authenticate user with username and password, issuing a JWT access token."""
```
**Incorrect Example:**
```python
@router.post("/login")  # Missing summary, docstring, and metadata
async def login(...):
    pass
```
**Exceptions:** Internal dev test endpoints active only when `DEBUG=True`.  
**Source:** `apps/backend/src/api/v1/routes/auth.py:66-82`.

---

### Rule ID: API-010
**Title:** Search and Filtering Query Parameters  
**Priority:** SHOULD  
**Rule:** 
- Free-text keyword search **SHOULD** use query parameter `q: str | None = Query(None, max_length=50)`.
- Category or role filters **SHOULD** match the exact database field name (e.g., `role: str | None = None`).
- Boolean flag filters **SHOULD** be prefixed with `is_` (e.g., `is_active: bool | None = None`).  
**Reason:** Establishes a uniform API querying convention across all list and search endpoints in the system.  
**Correct Example:**
```python
@router.get("/")
async def list_users(
    pagination: PaginationDep,
    q: str | None = Query(None, max_length=50, description="Search by username, email, or full name"),
    role: str | None = Query(None, description="Filter by role ('user' or 'admin')"),
    is_active: bool | None = Query(None, description="Filter by active status"),
):
    ...
```
**Incorrect Example:**
```python
@router.get("/")
async def list_users(
    keyword: str = "",      # Non-standard parameter name; use 'q'
    status_filter: int = 1, # Ambiguous naming convention
):
    ...
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/v1/routes/users.py:65-68`.
