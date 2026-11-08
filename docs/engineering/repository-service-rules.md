# HUCE-KMS — Repository & Service Layer Engineering Rules

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: Business Logic & Data Access Layer Architecture Standards  
> **Scope**: All modules in `api/repositories/` and `api/services/`  
> **Last Updated**: 2026-11-08  
> **Rule Prefix**: `REP-xxx`

---

## 1. Responsibility Partitioning Between Service and Repository

To maintain a lean, highly testable architecture without over-engineering, HUCE-KMS enforces strict boundaries between the Business Logic Layer (Services) and the Data Access Layer (Repositories):

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ ROUTE LAYER (api/v1/routes/*)                                               │
│ - Receives HTTP Request, parses DTOs, manages session cookies               │
│ - Invokes Service via Factory Dependency                                    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Calls Service Only)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ SERVICE LAYER (api/services/*)                                              │
│ - Owns 100% of Business Logic, domain validation, logical authorization     │
│ - Accepts DTOs/Primitives from Routes; converts Models to outgoing DTOs     │
│ - Coordinates 1 or more Repositories                                        │
│ - Raises domain exceptions (AppException subclasses)                        │
│ - MUST NEVER contain: HTTP Request/Response, SQL statements, commit() calls │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Calls Repository Only)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ REPOSITORY LAYER (api/repositories/*)                                       │
│ - Owns 100% of Database Queries (SQLAlchemy select, filter, join)           │
│ - Inherits from BaseRepository[ModelType] (get_by_id, list, create, update)  │
│ - Receives session: AsyncSession via constructor                            │
│ - Only calls session.flush(), NEVER commit()                                │
│ - MUST NEVER contain: Business logic, DTO transformations, HTTP objects     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Responsibility Matrix

| Action / Responsibility | Route Layer | Service Layer | Repository Layer |
| :--- | :---: | :---: | :---: |
| Extract Query / Path params / Body | **YES** | NO | NO |
| Manage Cookie headers (`Set-Cookie`) | **YES** | NO | NO |
| Check Admin Role / Resource Ownership | **YES** (HTTP level) | **YES** (Logic level) | NO |
| Hash Passwords (Argon2id) / Sign JWT | NO | **YES** | NO |
| Check Email / Username Uniqueness | NO | **YES** | NO |
| Raise Domain Exceptions (`ConflictException`, etc.) | NO | **YES** | NO |
| Transform Model $\rightarrow$ Pydantic Response DTO | NO | **YES** | NO |
| Write `select()`, `where()`, `offset()` queries | NO | NO | **YES** |
| Call `session.flush()` | NO | NO | **YES** |
| Call `session.commit()` | **YES** (via `get_db_session`) | NO | NO |

---

## 2. Repository & Service Rules Catalog

### Rule ID: REP-001
**Title:** Strict Architectural Separation Between Services and Repositories  
**Priority:** MUST  
**Rule:** 
- Route Handlers **MUST NOT** invoke Repositories or ORM Models directly, bypassing the Service Layer.
- Services **MUST NOT** construct raw SQL or execute direct SQLAlchemy queries (`select`, `execute`), delegating all query operations to Repositories.
- Repositories **MUST NOT** contain domain business rules, import response DTO schemas (except when strictly required), or raise HTTP exceptions.  
**Reason:** Enforces the Single Responsibility Principle (SRP) and Inversion of Control. Storage or schema refactoring only affects Repositories without leaking into business logic.  
**Correct Example:**
```python
# 1. Route calls Service
@router.get("/{user_id}")
async def get_user(user_id: int, service: UserServiceDep):
    user = await service.get_user_by_id(user_id)
    return BaseResponse(data=user)

# 2. Service handles logic and invokes Repository
class UserService:
    async def get_user_by_id(self, user_id: int) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException(entity_name="User", entity_id=user_id)
        return UserResponse.model_validate(user)

# 3. Repository executes database query
class UserRepository(BaseRepository[User]):
    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```
**Incorrect Example:**
```python
# Route invokes Repository directly -> Architectural violation!
@router.get("/{user_id}")
async def get_user(user_id: int, repo: UserRepositoryDep):
    user = await repo.get_by_id(user_id)
    return user
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/v1/routes/users.py:91-100`, `apps/backend/src/api/services/user.py:62-67`, `apps/backend/src/api/repositories/user.py:15-18`.

---

### Rule ID: REP-002
**Title:** Inherit `BaseRepository[ModelType]` for Standard CRUD Operations  
**Priority:** SHOULD  
**Rule:** Concrete entity repositories **SHOULD** inherit from `BaseRepository[ModelType]` (`api/repositories/base.py`) and invoke `super().__init__(ModelClass, session)`, reusing established CRUD methods:
- `get_by_id(self, id: Any) -> ModelType | None`
- `list(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]`
- `create(self, instance: ModelType) -> ModelType`
- `update(self, instance: ModelType) -> ModelType`
- `delete(self, instance: ModelType) -> None`  
**Reason:** Eliminates repetitive CRUD boilerplate across entities and standardizes `session.flush()` invocation.  
**Correct Example:**
```python
# api/repositories/user.py
class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    # Implement only domain-specific queries:
    async def get_by_username(self, username: str) -> User | None:
        ...
```
**Incorrect Example:**
```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Manually re-implementing get_by_id, create, update, delete repeatedly
    async def get_by_id(self, id: int):
        return await self.session.get(User, id)
```
**Exceptions:** Repositories that do not map to a single ORM table (e.g., aggregate analytical reporting repositories).  
**Source:** `apps/backend/src/api/repositories/base.py:11-44`, `apps/backend/src/api/repositories/user.py:9-13`.

---

### Rule ID: REP-003
**Title:** Constructor-Based Dependency Injection  
**Priority:** MUST  
**Rule:** 
- Repositories **MUST** receive `AsyncSession` via their `__init__` constructor.
- Services **MUST** receive their required Repositories via their `__init__` constructor.
- Classes **MUST NOT** import global session factories or instantiate database sessions inside method bodies.  
**Reason:** Decouples classes, enabling straightforward injection of mock sessions and mock repositories during Unit Testing.  
**Correct Example:**
```python
# Repository
class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession):
        super().__init__(RefreshToken, session)

# Service
class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
    ):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo
```
**Incorrect Example:**
```python
class AuthService:
    def __init__(self):
        # Hardcoding repo and session creation prevents test mocking
        self.user_repo = UserRepository(async_session_factory())
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/services/auth.py:21-30`, `apps/backend/src/api/repositories/refresh_token.py:9-13`.

---

### Rule ID: REP-004
**Title:** Strict Prohibition of HTTP Objects in Services and Repositories  
**Priority:** MUST  
**Rule:** Service and Repository classes **MUST NOT** accept parameters representing HTTP transport objects from FastAPI/Starlette (e.g., `Request`, `Response`, `UploadFile`, `Cookie`, `Header`, `BackgroundTasks`). All arguments passed into Services **MUST** be primitive types (str, int, bool) or Pydantic DTO Schemas.  
**Reason:** Keeps the Service Layer transport-agnostic, allowing business methods to be called from CLI commands, background workers (Celery/Arq), or asynchronous job queues without synthesizing fake HTTP requests.  
**Correct Example:**
```python
# Route handler extracts metadata from Request and passes primitives to Service:
@router.post("/login")
async def login(payload: UserLogin, request: Request, service: AuthServiceDep):
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None

    user, access_token, refresh_token = await service.login(
        payload=payload,
        user_agent=user_agent,
        ip_address=client_ip,
    )
```
**Incorrect Example:**
```python
# Passing the HTTP Request object directly into the service:
class AuthService:
    async def login(self, payload: UserLogin, request: Request): # FORBIDDEN
        user_agent = request.headers.get("user-agent")
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/v1/routes/auth.py:83-96`, `apps/backend/src/api/services/auth.py:56-66`.

---

### Rule ID: REP-005
**Title:** Transaction Ownership and Unit of Work Lifecycle  
**Priority:** MUST  
**Rule:** 
- Transaction ownership belongs exclusively to the `DatabaseDep` (`get_db_session`) request dependency.
- Repositories ONLY stage changes into the database buffer using `await self.session.flush()`.
- Services **MUST NOT** call `commit()` or `rollback()` directly. To roll back a transaction, a service simply raises an exception (e.g., `AppException`).  
**Reason:** Guarantees data consistency across complex multi-repository workflows. If any step fails, all prior modifications roll back cleanly at the request boundary.  
**Correct Example:**
```python
# api/services/auth.py
async def register(self, payload: UserCreate) -> UserResponse:
    # 1. Check uniqueness
    if await self.user_repo.get_by_username(payload.username):
        raise ConflictException(message="Username taken")

    # 2. Persist user (Repository only flushes)
    created_user = await self.user_repo.create(user)
    
    # 3. Return DTO -> Request completes -> get_db_session automatically commits!
    return UserResponse.model_validate(created_user)
```
**Incorrect Example:**
```python
async def register(self, payload: UserCreate):
    created_user = await self.user_repo.create(user)
    await self.user_repo.session.commit() # FORBIDDEN: Service/repo must not commit
    return created_user
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/dependencies.py:41-54`, `apps/backend/src/api/services/auth.py:32-54`.

---

### Rule ID: REP-006
**Title:** Domain Error Signalling via `AppException`  
**Priority:** MUST  
**Rule:** When business conditions are violated in the Service Layer, developers **MUST** raise subclasses of `AppException` (`ConflictException`, `BadRequestException`, `EntityNotFoundException`, `UnauthorizedException`, `ForbiddenException`). Services **MUST NOT** return error dictionaries (e.g., `{"status": "error"}`) or return `None` when a failure requires user notification.  
**Reason:** Automatically triggers transaction rollback in `get_db_session` and hands over control to Global Exception Handlers, guaranteeing uniform HTTP status codes and error JSON payloads.  
**Correct Example:**
```python
# api/services/user.py
async def get_user_by_id(self, user_id: int) -> UserResponse:
    user = await self.user_repo.get_by_id(user_id)
    if not user:
        raise EntityNotFoundException(entity_name="User", entity_id=user_id)
    return UserResponse.model_validate(user)
```
**Incorrect Example:**
```python
async def get_user_by_id(self, user_id: int):
    user = await self.user_repo.get_by_id(user_id)
    if not user:
        return None # Returning None forces manual checking in routes!
    return user
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/services/user.py:62-67`.

---

### Rule ID: REP-007
**Title:** Model-to-DTO Transformation Owned by Service Layer  
**Priority:** MUST  
**Rule:** The Service Layer **MUST** convert ORM Models returned by Repositories into Pydantic Response DTOs (via `ResponseModel.model_validate(orm_model)`) before returning data to Route handlers.  
**Reason:** Prevents internal ORM model state from leaking into Route controllers and avoids detached-instance attribute access errors outside the active async session.  
**Correct Example:**
```python
# Service returns UserResponse (Pydantic DTO)
async def update_user(self, user_id: int, payload: UserUpdate) -> UserResponse:
    ...
    updated_user = await self.user_repo.update(user)
    return UserResponse.model_validate(updated_user)
```
**Incorrect Example:**
```python
# Service returns SQLAlchemy ORM Model to Route
async def update_user(self, user_id: int, payload: UserUpdate) -> User:
    ...
    return await self.user_repo.update(user)
```
**Exceptions:** Private helper methods within a service (`_get_user_model`) executing subsequent mutations in the same transaction.  
**Source:** `apps/backend/src/api/services/user.py:80-81`.

---

### Rule ID: REP-008
**Title:** Repository Method Naming Standards  
**Priority:** MUST  
**Rule:** 
- Single-entity query methods: `get_by_<field>(self, value: T) -> Model | None`.
- Paginated search with count: `search_with_count(self, ...) -> tuple[Sequence[Model], int]`.
- Specialized state mutations: `revoke(self, ...)`, `revoke_all_for_user(self, user_id: int)`.
- List results **MUST** be typed as `collections.abc.Sequence[Model]`.  
**Reason:** Synchronizes repository interfaces across the project, ensuring predictable method signatures and type safety.  
**Correct Example:**
```python
# api/repositories/user.py
async def get_by_username(self, username: str) -> User | None:
    ...

async def search_with_count(
    self,
    q: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 10,
) -> tuple[Sequence[User], int]:
    ...
```
**Incorrect Example:**
```python
async def find_user(self, name: str): ... # Ambiguous name, untyped
async def query_users(self, ...): ...
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/repositories/user.py:15-32`.

---

### Rule ID: REP-009
**Title:** Prevention of Inter-Service Circular Dependencies  
**Priority:** SHOULD  
**Rule:** 
- A Service MAY receive multiple distinct Repositories in its constructor (e.g., `UserService` receives both `UserRepository` and `RefreshTokenRepository`).
- When two services require shared operations, developers **SHOULD** extract the shared logic into a common Repository or dedicated infrastructure Service. Services **MUST NEVER** import each other bidirectionally (`AuthService` $\leftrightarrow$ `UserService`).  
**Reason:** Prevents Python Circular Import Errors and dependency graph cycles in FastAPI dependency injection.  
**Correct Example:**
```python
# Both AuthService and UserService depend unidirectionally on repositories:
class AuthService:
    def __init__(self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository):
        ...

class UserService:
    def __init__(self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository):
        ...
```
**Incorrect Example:**
```python
class AuthService:
    def __init__(self, user_service: UserService): # AuthService depends on UserService
        ...
class UserService:
    def __init__(self, auth_service: AuthService): # UserService depends on AuthService -> CIRCULAR!
        ...
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/services/auth.py:24-30`, `apps/backend/src/api/services/user.py:13-19`.

---

### Rule ID: REP-010
**Title:** Lean Architecture (No Over-Engineering)  
**Priority:** SHOULD  
**Rule:** The codebase deliberately avoids superfluous enterprise abstractions, such as separate custom UnitOfWork classes (as SQLAlchemy's session is already a complete Unit of Work) or abstract interfaces (ABCs) for every Service/Repository when only a single implementation exists. Keep code direct, explicit, and maintainable.  
**Reason:** Minimizes unnecessary boilerplate files, facilitating quick code navigation for developers and AI coding agents.  
**Correct Example:**
```python
# Concrete UserService declaration:
class UserService:
    def __init__(self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository):
        ...
```
**Incorrect Example:**
```python
# Redundant enterprise boilerplate:
class IUserRepository(ABC): ...
class IUserService(ABC): ...
class UnitOfWork(ABC): ...
class SqlAlchemyUnitOfWork(UnitOfWork): ...
```
**Exceptions:** When the system genuinely requires supporting multi-database backends simultaneously (e.g., supporting both PostgreSQL and MongoDB). Currently, the platform standardizes entirely on SQLAlchemy.  
**Source:** Active codebase implementation in `apps/backend/src/api/services/`, `apps/backend/src/api/repositories/`.
