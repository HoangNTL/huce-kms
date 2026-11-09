# HUCE-KMS — Automated Testing Rules

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: Automated Testing Guidelines, Fixtures & Async Test Architecture  
> **Target**: Entire test suite in `apps/backend/tests/`  
> **Last Updated**: 2026-11-08  
> **Rule ID Prefix**: `TST-xxx`

---

## 1. Testing Strategy & Current Reality

### Active Runtime Reality
- The `tests/` directory **does not currently exist** in `apps/backend`.
- Automated testing dependencies (`pytest`, `pytest-asyncio`, `httpx`) **are not yet added** to `pyproject.toml` or `uv.lock`.
- Verification is currently conducted via Swagger UI (`/docs`), script import assertions (`uv run python -c "..."`), and mock tokens in `DEBUG` mode.

### Engineering Test Architecture (Phase 2.1 Target)
This document establishes mandatory engineering rules for building the backend automated test suite upon dependency installation:

Testing is structured into 3 distinct tiers:
1. **Unit Tests (`tests/unit/`)**: Verify isolated business logic in Services, Password Hashing, Token generation, and Pydantic validation (< 1ms/test execution).
2. **Integration Tests (`tests/integration/`)**: Verify Repository interactions with database (using isolated test databases or rollbacked transactions).
3. **API / End-to-End Tests (`tests/api/`)**: Verify complete HTTP request lifecycles via `httpx.AsyncClient`, covering middleware, dependency injection, cookies, and `BaseResponse` schemas.

---

## 2. Testing Rules Catalog

### Rule ID: TST-001
**Title:** Testing Toolchain Standard  
**Priority:** SHOULD  
**Rule:** The backend testing toolchain **SHOULD** adopt standard asynchronous libraries:
- Test runner: `pytest >= 8.0`
- Async runner plugin: `pytest-asyncio >= 0.23`
- Asynchronous HTTP client: `httpx >= 0.27`
These packages will be managed under `uv` development dependencies:
```bash
cd apps/backend
uv add --dev pytest pytest-asyncio httpx
```  
**Reason:** Guarantees seamless compatibility with FastAPI asynchronous ASGI architecture, allowing high-performance HTTP testing without running a live Uvicorn socket server.  
**Correct Example:**
```toml
# pyproject.toml (Target configuration)
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]
```
**Incorrect Example:**
```bash
# Using standard synchronous unittest or blocking requests library that halts the event loop
```
**Exceptions:** None.  
**Source:** Target engineering toolchain for Phase 2.1.

---

### Rule ID: TST-002
**Title:** Test Directory & File Structure  
**Priority:** MUST  
**Rule:** The test suite **MUST** follow a structured hierarchy inside `apps/backend/tests/`:
```text
apps/backend/tests/
├── conftest.py               # Shared fixtures for the test suite
├── api/                      # API endpoint tests (HTTP status, BaseResponse, cookies)
│   ├── test_auth.py
│   └── test_users.py
├── unit/                     # Isolated service logic & utility tests
│   ├── test_auth_service.py
│   ├── test_user_service.py
│   └── test_security.py
└── integration/              # Repository & database interaction tests
    ├── test_user_repo.py
    └── test_refresh_token_repo.py
```
Test filenames **MUST** use the `test_` prefix in `snake_case.py`.  
**Reason:** Enables standard pytest test discovery and permits selective execution by test category.  
**Correct Example:**
`tests/api/test_auth.py`, `tests/unit/test_security.py`.  
**Incorrect Example:**
`tests/auth_test.py`, `tests/testAuth.py`.  
**Exceptions:** Test configuration files like `conftest.py` or fixture data files (`fixtures.json`).  
**Source:** Pytest standard practices and HUCE-KMS repository layout.

---

### Rule ID: TST-003
**Title:** Test Function Naming Convention  
**Priority:** MUST  
**Rule:** Test function names **MUST** begin with `test_` and follow a descriptive action-expectation format:
```text
test_<action>_<expected_result>()
# or
test_<action>_when_<condition>_<expected_result>()
```
Names must be descriptive enough to diagnose failures without reading the implementation code.  
**Reason:** Acts as living technical documentation of expected system behavior.  
**Correct Example:**
```python
async def test_register_success(): ...
async def test_register_when_username_exists_raises_conflict(): ...
async def test_login_when_password_invalid_raises_unauthorized(): ...
async def test_update_status_when_admin_deactivates_self_raises_bad_request(): ...
```
**Incorrect Example:**
```python
async def test_1(): ...
async def test_user(): ...
async def test_register_error(): ...  # Ambiguous conditions and error types
```
**Exceptions:** None.  
**Source:** Clean code testing conventions.

---

### Rule ID: TST-004
**Title:** Async Test Function Declaration  
**Priority:** MUST  
**Rule:** Every asynchronous test function using `async def` and `await` **MUST** be decorated with `@pytest.mark.asyncio` (or run with `asyncio_mode = "auto"` in `pyproject.toml`).  
**Reason:** Ensures pytest establishes an isolated event loop for async test execution, preventing `RuntimeError: Task was destroyed but it is pending`.  
**Correct Example:**
```python
import pytest

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "Password123@"},
    )
    assert response.status_code == 200
```
**Incorrect Example:**
```python
# Missing @pytest.mark.asyncio -> pytest skips or fails to execute coroutine
async def test_login_success():
    ...
```
**Exceptions:** Synchronous pure unit tests (e.g., password hashing tests).  
**Source:** FastAPI & `pytest-asyncio` standards.

---

### Rule ID: TST-005
**Title:** Test Database Isolation  
**Priority:** MUST  
**Rule:** Automated tests **MUST NEVER RUN** against the active development database. Every test session **MUST** use an isolated database instance:
- An isolated test database instance (such as a temporary test database, test container, or rollbacked transactions).
- Each test case **MUST** run within an isolated transaction that is rolled back or cleaned up upon completion, ensuring zero state contamination between test cases (Test Independence).  
**Reason:** Guarantees reproducibility and eliminates flaky tests caused by residual data from previous test runs.  
**Correct Example:**
```python
# tests/conftest.py
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="function")
async def db_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await test_engine.dispose()
```
**Incorrect Example:**
```python
# Running tests directly against live application database:
# Corrupts admin/user data and produces duplicate username errors on subsequent runs!
```
**Exceptions:** None.  
**Source:** `api/core/database.py` architecture and database testing principles.

---

### Rule ID: TST-006
**Title:** Dependency Overrides with `app.dependency_overrides`  
**Priority:** MUST  
**Rule:** When testing API endpoints via `httpx.AsyncClient`, tests **MUST** use FastAPI `app.dependency_overrides` to substitute:
1. `get_db_session`: Replaced with an isolated test database session.
2. `get_current_user`: When simulating authenticated users or testing admin access without performing full login calls.  
After each test case, fixtures **MUST** clear overrides with `app.dependency_overrides.clear()`.  
**Reason:** Accelerates test execution and tests authorization branches independently of the physical user table.  
**Correct Example:**
```python
# tests/api/test_users.py
@pytest.mark.asyncio
async def test_admin_can_list_users(client: AsyncClient, admin_user: CurrentUser):
    app.dependency_overrides[get_current_user] = lambda: admin_user

    response = await client.get("/api/v1/users/")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["success"] is True
```
**Incorrect Example:**
```python
# Calling POST /register -> POST /login -> attaching headers for every single RBAC test
# Slows test execution and causes cascade failures when login is broken
```
**Exceptions:** Explicit test cases dedicated to testing authentication and login flows (`/auth/login`, `/auth/me`).  
**Source:** FastAPI Dependency Injection testing patterns.

---

### Rule ID: TST-007
**Title:** API Response Schema Assertions  
**Priority:** MUST  
**Rule:** Every test case verifying an API endpoint **MUST** assert at least 4 criteria:
1. **HTTP Status Code**: Matches expected code (`200`, `201`, `400`, `401`, `403`, `404`, `409`, `422`).
2. **Envelope `success`**: Matches `True` (success) or `False` (error).
3. **Error `code`**: For error responses, verifies the business error code string (e.g., `code == "ENTITY_NOT_FOUND"`).
4. **Payload `data`**: Ensures data integrity and verifies sensitive fields like `hashed_password` are excluded.  
**Reason:** Guarantees that the API Contract between Backend and Frontend remains intact across refactors.  
**Correct Example:**
```python
@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient, admin_user: CurrentUser):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    response = await client.get("/api/v1/users/99999")
    app.dependency_overrides.clear()

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "ENTITY_NOT_FOUND"
    assert "User with ID '99999' not found." in body["message"]
    assert body["data"] is None
```
**Incorrect Example:**
```python
# Only asserting status 404 without validating envelope structure:
assert response.status_code == 404
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/exceptions.py:140-147`, `apps/backend/src/api/schemas/common.py:37-43`.

---

### Rule ID: TST-008
**Title:** RBAC & Security Boundary Testing  
**Priority:** MUST  
**Rule:** For each protected endpoint, tests **MUST** cover at least 3 scenarios:
1. **Happy Path**: Caller holds valid permissions (e.g., Admin access $\rightarrow$ 200/201 Success).
2. **Unauthorized Case**: Missing or invalid token $\rightarrow$ 401 Unauthorized.
3. **Forbidden Case**: Valid token with insufficient permissions (e.g., regular user accessing admin endpoint, or updating another user's profile) $\rightarrow$ 403 Forbidden.  
**Reason:** Prevents Privilege Escalation and IDOR vulnerabilities from reaching production.  
**Correct Example:**
```python
@pytest.mark.asyncio
async def test_standard_user_cannot_create_user(client: AsyncClient, regular_user: CurrentUser):
    app.dependency_overrides[get_current_user] = lambda: regular_user
    response = await client.post("/api/v1/users/", json={...})
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
```
**Incorrect Example:**
```python
# Testing only admin happy path while omitting user boundary restriction tests
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/dependencies.py:160-174`, `apps/backend/src/api/v1/routes/users.py:44, 93-94`.

---

### Rule ID: TST-009
**Title:** Reasonable Mocking Boundaries  
**Priority:** SHOULD  
**Rule:** 
- **RECOMMENDED TO MOCK**: Slow or costly external integrations (email dispatch, external LLM APIs like OpenAI/Gemini, external Vector Database endpoints).
- **DO NOT MOCK**: Do not mock Service layers in API tests, and do not mock Repository/Session layers in database integration tests (outside of isolated unit tests).  
**Reason:** Over-mocking yields tests that only test their own mocks and fail to detect real runtime failures.  
**Correct Example:**
```python
# Mocking embedding generation in RAG pipeline tests
@pytest.fixture
def mock_embedding_service(monkeypatch):
    async def fake_embed(text: str) -> list[float]:
        return [0.1] * 1536
    monkeypatch.setattr("api.services.rag.generate_embedding", fake_embed)
```
**Incorrect Example:**
```python
# Mocking user_repo.create() to return a fake object in API integration tests:
# Leaves actual SQL queries untested against SQLite/PostgreSQL!
```
**Exceptions:** Pure unit tests executing isolated functions with zero I/O.  
**Source:** Best practices in automated testing architecture.

---

### Rule ID: TST-010
**Title:** Risk-Based Test Coverage  
**Priority:** SHOULD  
**Rule:** Avoid targeting 100% test coverage dogmatically. Testing **SHOULD** prioritize high-risk system components:
1. Security layer, Password Hashing, JWT creation & decoding, Refresh Token Rotation.
2. RBAC rules and IDOR ownership verifications.
3. Complex business computations and state machine transitions in Services.
4. Exception handling and database transaction atomicity.  
**Reason:** Maximizes developer efficiency by focusing test verification on components with the greatest potential failure impact.  
**Correct Example:**
Prioritizing 100% test coverage on `AuthService` and `UserService` before testing simple static lookup endpoints.  
**Incorrect Example:**
Spending testing effort on simple getters/setters solely to satisfy coverage metrics.  
**Exceptions:** None.  
**Source:** HUCE-KMS Monorepo quality guidelines.
