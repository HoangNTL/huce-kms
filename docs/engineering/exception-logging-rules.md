# HUCE-KMS — Exception Handling & Logging Engineering Rules

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: Exception Hierarchy, Error Response & Centralized Logging Standards  
> **Scope**: All architectural layers in `apps/backend`  
> **Last Updated**: 2026-11-08  
> **Rule Prefix**: `EXC-xxx`

---

## 1. Exception Hierarchy Overview

All domain business exceptions in HUCE-KMS are built upon the foundational `AppException` base class (defined in `api/core/exceptions.py`):

```text
Exception (Built-in Python)
 └── AppException (api.core.exceptions)
      ├── EntityNotFoundException (404 Not Found - ENTITY_NOT_FOUND)
      │    └── NotFoundException (Backward-compatible alias)
      ├── BadRequestException (400 Bad Request - BAD_REQUEST)
      ├── UnauthorizedException (401 Unauthorized - UNAUTHORIZED)
      ├── ForbiddenException (403 Forbidden - FORBIDDEN)
      └── ConflictException (409 Conflict - CONFLICT)
```

### Standard Error Response Envelope (`format_error_response`)

Every error returned to clients (whether arising from `AppException`, a Pydantic 422 schema validation error, or an unhandled 500 server error) is normalized into a consistent JSON envelope:

```json
{
  "success": false,
  "code": "<ERROR_CODE_STRING>",
  "message": "<User-friendly error description>",
  "details": null,
  "data": null
}
```

---

## 2. Exception & Logging Rules Catalog

### Rule ID: EXC-001
**Title:** Mandatory Inheritance from `AppException` for Domain Exceptions  
**Priority:** MUST  
**Rule:** All custom domain exceptions **MUST** inherit directly from `AppException` (or one of its specialized subclasses) and pass 4 arguments through `super().__init__()`:
- `status_code`: Semantic HTTP status code (`status.HTTP_4xx_...`).
- `error_code`: Machine-readable `UPPER_SNAKE_CASE` string identifier (e.g., `DOCUMENT_NOT_FOUND`).
- `message`: Clear, user-safe description message suitable for UI display.
- `details`: Optional structured dictionary or list with context metadata.  
**Reason:** Allows global exception handlers to automatically catch and format errors without writing bespoke handlers for each exception.  
**Correct Example:**
```python
# api/core/exceptions.py
class EntityNotFoundException(AppException):
    def __init__(
        self,
        entity_name: str = "Resource",
        entity_id: Any = None,
        message: str | None = None,
        details: Any = None,
    ):
        if not message:
            message = (
                f"{entity_name} with ID '{entity_id}' not found."
                if entity_id is not None
                else f"{entity_name} not found."
            )
        default_details = (
            {"entity_name": entity_name, "entity_id": entity_id}
            if entity_id is not None
            else {"entity_name": entity_name}
        )
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ENTITY_NOT_FOUND",
            message=message,
            details=details if details is not None else default_details,
        )
```
**Incorrect Example:**
```python
# Raising Python's raw Exception in a service
raise Exception("User not found") # Treated as an unhandled 500 server error!
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/exceptions.py:15-60`.

---

### Rule ID: EXC-002
**Title:** Prohibition of Error Dictionaries or Return Codes in Services  
**Priority:** MUST  
**Rule:** When business conditions fail in the Service Layer, services **MUST** raise `raise AppException(...)`. Services **MUST NEVER** return error dictionaries (e.g., `return {"success": False, "error": "..."}`) or return `None` to signal an exceptional failure.  
**Reason:** 
1. Raising an exception immediately halts execution and triggers the automatic `session.rollback()` cycle in the request lifecycle dependency.
2. Prevents contaminating function signatures with union error types (e.g., avoiding `-> UserResponse | dict[str, Any]`).  
**Correct Example:**
```python
if existing_email:
    raise ConflictException(message=f"Email '{payload.email}' is already registered.")
```
**Incorrect Example:**
```python
if existing_email:
    return {"error": "Email registered", "status": 409} # FORBIDDEN: Forces manual checking in controllers
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/services/auth.py:40-42`.

---

### Rule ID: EXC-003
**Title:** Centralized Global Exception Handler Registration  
**Priority:** MUST  
**Rule:** All exceptions escaping route execution **MUST** be routed through the 4 centralized handlers registered in `api/core/exceptions.py:register_exception_handlers`:
1. `app_exception_handler`: Catches all `AppException` domain errors.
2. `http_exception_handler`: Catches `StarletteHTTPException` (standardizing 404 and 405 framework errors).
3. `validation_exception_handler`: Catches `RequestValidationError` (standardizing Pydantic 422 errors into structured arrays `[{"field": ..., "message": ...}]`).
4. `unhandled_exception_handler`: Catches `Exception` (unexpected 500 server errors).  
**Reason:** Ensures external clients always receive a uniform JSON response envelope regardless of where or how a runtime failure occurred.  
**Correct Example:**
```python
# api/core/exceptions.py
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
```
**Incorrect Example:**
```python
# Wrapping individual route handlers in manual try/except blocks
@router.get("/{id}")
async def get_item(id: int):
    try:
        ...
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/exceptions.py:240-245`.

---

### Rule ID: EXC-004
**Title:** Stack Trace Concealment on 500 Server Errors  
**Priority:** MUST  
**Rule:** When unhandled 500 errors occur (`unhandled_exception_handler`), the system **MUST** log the full traceback to disk using `logger.exception(...)`, but **MUST NEVER** send tracebacks, filenames, or source snippets to the client in the JSON response. The client response message MUST be a safe generic message: `"An unexpected server error occurred. Please contact administrator."`.  
**Reason:** Eliminates Information Disclosure Vulnerabilities that could reveal database schemas, internal paths, library versions, or failed SQL queries to attackers.  
**Correct Example:**
```python
# api/core/exceptions.py
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Full traceback logged on server
    logger.exception("Unhandled Exception on [%s %s]: %s", request.method, request.url.path, exc)
    
    # Safe generic payload returned to client
    return format_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please contact administrator.",
        details=None,
    )
```
**Incorrect Example:**
```python
# Returning raw exception details directly to the client:
return JSONResponse(
    status_code=500,
    content={"message": str(exc), "traceback": traceback.format_exc()} # CRITICAL SECURITY RISK
)
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/exceptions.py:221-235`.

---

### Rule ID: EXC-005
**Title:** Named Hierarchical Loggers (`huce_kms.*`)  
**Priority:** MUST  
**Rule:** Each module **MUST** instantiate its own logger using the `huce_kms.<module_name>` namespace:
```python
import logging
logger = logging.getLogger("huce_kms.<module_name>")
```
Using `print()` or an anonymous root logger (`logging.getLogger()`) is **STRICTLY PROHIBITED**.  
**Reason:** Enables granular log-level filtering and selective debugging per module without flooding system-wide logs.  
**Correct Example:**
```python
# api/services/auth.py
logger = logging.getLogger("huce_kms.auth")

# api/core/middleware.py
logger = logging.getLogger("huce_kms.http")

# api/core/lifespan.py
logger = logging.getLogger("huce_kms.lifespan")
```
**Incorrect Example:**
```python
print(f"User {user_id} logged in") # print is strictly forbidden
logger = logging.getLogger()       # Do not use the anonymous root logger
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/services/auth.py:18`, `apps/backend/src/api/core/middleware.py:12`, `apps/backend/src/api/core/lifespan.py:14`.

---

### Rule ID: EXC-006
**Title:** Request Correlation via `X-Request-ID` and Latency Tracking  
**Priority:** MUST  
**Rule:** Every HTTP request entering the application **MUST** be assigned a unique `request_id` (8-character short UUID) by `RequestLifecycleMiddleware`. This ID is injected into `request.state.request_id`, attached to the `X-Request-ID` response header, and emitted in every HTTP access log alongside the elapsed execution time (`X-Process-Time` in ms).  
**Reason:** Enables operational engineers and AI agents to correlate and trace all events belonging to a specific transaction in log files during production incidents.  
**Correct Example:**
```python
# api/core/middleware.py
request_id = str(uuid.uuid4())[:8]
request.state.request_id = request_id
start_time = time.perf_counter()

response = await call_next(request)

process_time_ms = (time.perf_counter() - start_time) * 1000
response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"
response.headers["X-Request-ID"] = request_id

logger.info(
    "[%s] %s %s -> Status: %d (%.2fms)",
    request_id,
    request.method,
    request.url.path,
    response.status_code,
    process_time_ms,
)
```
**Incorrect Example:**
```python
# Logging without a request_id makes concurrent requests indistinguishable
logger.info("Request completed with status 200")
```
**Exceptions:** Static documentation and probe endpoints do not log access to prevent log noise: `/health`, `/docs`, `/redoc`, `/openapi.json`, `/favicon.ico`.  
**Source:** `apps/backend/src/api/core/middleware.py:15-49`.

---

### Rule ID: EXC-007
**Title:** Log Redaction Policy for Sensitive Data  
**Priority:** MUST  
**Rule:** Across all logging calls (`logger.info`, `logger.debug`, `logger.error`), developers **MUST NEVER** output:
- Raw or hashed passwords.
- Access tokens, Refresh tokens, API keys, or Private keys.
- Full values of `Authorization` or `Cookie` headers.
- Personally Identifiable Information (national IDs, credit card numbers).  
**Reason:** Prevents credential compromise and complies with data privacy regulations. Log files are frequently replicated across storage and observability systems.  
**Correct Example:**
```python
logger.info("Authentication attempt for username='%s'", payload.username)
logger.warning("Token reuse detected for user_id=%d", user.id)
```
**Incorrect Example:**
```python
logger.info("User login: username='%s', password='%s'", payload.username, payload.password) # CREDENTIAL EXPOSURE
logger.info("Received refresh token: %s", raw_refresh_token) # TOKEN EXPOSURE
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/services/auth.py:117-120`.

---

### Rule ID: EXC-008
**Title:** Rotating File Logging Configuration  
**Priority:** MUST  
**Rule:** The system **MUST** configure combined Console (`StreamHandler`) and rotating file logging (`RotatingFileHandler`) in `api/core/logging.py`:
- Log file destination: `apps/backend/logs/app.log`.
- Maximum size per file: `10MB` (`maxBytes=10 * 1024 * 1024`).
- Maximum backup files: `5` (`backupCount=5`).
- Encoding: `utf-8`.
- Standard format: `%(asctime)s | %(levelname)-7s | %(name)s | %(message)s`.  
**Reason:** Prevents disk space exhaustion on server hosts over long-running deployments.  
**Correct Example:**
```python
# api/core/logging.py
file_handler = logging.handlers.RotatingFileHandler(
    filename=LOGS_DIR / "app.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
```
**Incorrect Example:**
```python
# Unbounded log growth without size limits or rotation
logging.basicConfig(filename="app.log")
```
**Exceptions:** Containerized environments using specialized log aggregators (e.g., Fluentbit, Promtail/Loki) requiring stdout-only output.  
**Source:** `apps/backend/src/api/core/logging.py:11-48`.

---

### Rule ID: EXC-009
**Title:** Semantic Log Levels Usage  
**Priority:** SHOULD  
**Rule:** Log statements **SHOULD** adhere strictly to contextual severity levels:
- `DEBUG`: Granular technical diagnostic details (query strings, dev environment configurations).
- `INFO`: Normal lifecycle events (application startup, successful data seeding, completed requests, user logins).
- `WARNING`: Recoverable anomalies handled by the system (token expiration, detected token reuse, 403 access denials, unfamiliar CORS origins).
- `ERROR`: Unhandled business exceptions or database errors disrupting a user request.
- `CRITICAL`: Severe system-wide failures (inability to connect to the database on startup).  
**Reason:** Facilitates accurate alerting and filtering during incident response.  
**Correct Example:**
```python
logger.info("[SEEDER] Created default admin account: 'admin'")
logger.warning("Revoked refresh token reused for user_id=%d", user_id)
logger.error("[STARTUP] Database schema initialization failed: %s", e)
```
**Incorrect Example:**
```python
logger.error("User entered wrong password") # Incorrect severity: failed login is a warning/debug event
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/lifespan.py:35, 65`, `apps/backend/src/api/services/auth.py:117`.

---

### Rule ID: EXC-010
**Title:** Single-Point Error Logging Policy  
**Priority:** SHOULD  
**Rule:** When an error occurs, it **SHOULD** be logged at a **single point of responsibility** (either where it is initially caught or at the Global Exception Handler). Avoid multi-tier logging anti-patterns where a Repository logs an error, re-raises it to the Service, which logs it again and re-raises it to the Controller, which logs it a third time.  
**Reason:** Prevents log dilution and false alarms indicating multiple failures when only a single root event occurred.  
**Correct Example:**
```python
# Service simply raises the domain exception
if not user:
    raise EntityNotFoundException(entity_name="User", entity_id=user_id)

# Global exception handler logs appropriately (DEBUG for 404, ERROR for 500)
```
**Incorrect Example:**
```python
# Logging the same 404 error across three layers:
# 1. Repository: logger.error("User not found")
# 2. Service: logger.error("User not found in service")
# 3. Route: logger.error("Get user endpoint failed")
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/exceptions.py:153-178`.
