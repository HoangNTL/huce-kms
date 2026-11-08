# HUCE-KMS — Schema & Validation Engineering Rules

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: Data Transfer Object (DTO) & Pydantic V2 Validation Standards  
> **Scope**: All DTOs in `apps/backend/src/api/schemas/`  
> **Last Updated**: 2026-11-08  
> **Rule Prefix**: `SCH-xxx`

---

## 1. Validation Boundaries & Tier Partitioning

To avoid redundant validation logic across architectural layers, HUCE-KMS defines four clear validation tiers:

1. **Syntax & Data Type Validation (Schema Input Validation - Pydantic)**:
   - *Scope*: Formatting, data types, string length bounds (`min_length`, `max_length`), numerical limits (`ge`, `le`), email formats (`EmailStr`), enum literals (`Literal`).
   - *Executed by*: Schemas layer via Pydantic V2.
   - *Failure response*: Automatically returns HTTP `422 Unprocessable Entity` via `validation_exception_handler`.
2. **Domain Business Validation (Business Validation - Services)**:
   - *Scope*: Uniqueness constraints (does username/email already exist?), current password verification, account active checks, logical authorization (admins cannot demote themselves).
   - *Executed by*: Service layer.
   - *Failure response*: Raises domain `AppException` subclasses (`ConflictException`, `BadRequestException`, `ForbiddenException`).
3. **Data Integrity Constraints (Database Constraints - SQLAlchemy / Database)**:
   - *Scope*: Primary keys (PK), foreign keys (FK with `ON DELETE CASCADE`), `UNIQUE INDEX`, `NOT NULL` columns.
   - *Executed by*: Models layer and the Database Engine (SQLite / PostgreSQL).
4. **Data Serialization (Serialization - Pydantic Response DTOs)**:
   - *Scope*: Filtering and transforming ORM models into secure outgoing JSON responses, stripping internal fields (such as `hashed_password`).

---

## 2. Schema & Validation Rules Catalog

### Rule ID: SCH-001
**Title:** Pydantic V2 Syntax Exclusivity  
**Priority:** MUST  
**Rule:** All schemas **MUST** use standard Pydantic V2 syntax:
- Schema configuration via `model_config = ConfigDict(...)` (imported from `pydantic`).
- Conversion from ORM models via `ModelSchema.model_validate(orm_obj)`.
- Exporting to dictionaries via `schema.model_dump(...)`.
- Deprecated Pydantic V1 syntax (`class Config: orm_mode = True`, `.from_orm()`, `.dict()`, `.parse_obj()`) is **STRICTLY FORBIDDEN**.  
**Reason:** Pydantic V2 is powered by Rust (`pydantic-core`), delivering 5–17x faster serialization/validation than V1 and avoiding deprecation warnings.  
**Correct Example:**
```python
from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)

# Data transformation:
dto = UserResponse.model_validate(orm_user)
payload_dict = payload.model_dump(exclude_unset=True)
```
**Incorrect Example:**
```python
class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True  # Deprecated V1 Syntax

dto = UserResponse.from_orm(orm_user)      # Deprecated V1 Method
payload_dict = payload.dict()              # Deprecated V1 Method
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/schemas/user.py:60`.

---

### Rule ID: SCH-002
**Title:** Clear Separation of Base, Create, Update, and Response DTOs  
**Priority:** MUST  
**Rule:** Every domain entity **MUST** provide specialized DTOs for each data flow boundary:
1. `<Entity>Base`: Shared fundamental fields common to creation and display.
2. `<Entity>Create`: Public creation payload (inheriting `Base`, adding password/defaults).
3. `Admin<Entity>Create`: Privileged administrative creation payload (adding role/status overrides).
4. `<Entity>Update`: General update payload with optional fields.
5. `<Entity><Field>Update`: Specialized single-purpose update payload (e.g., `UserStatusUpdate`, `UserRoleUpdate`).
6. `<Entity>Response`: Outgoing response payload (`id`, `created_at`, `updated_at`, `from_attributes=True`).
A single Pydantic model **MUST NOT** be shared between request bodies and response models.  
**Reason:** Prevents Mass Assignment Vulnerabilities, stopping clients from manipulating internal attributes such as `id`, `role`, or `created_at`.  
**Correct Example:**
```python
# Base
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None

# Create (Clients only register with default role 'user')
class UserCreate(UserBase):
    password: str

# Update
class UserUpdate(BaseModel):
    full_name: str | None = None

# Response
class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```
**Incorrect Example:**
```python
# Sharing a single model for both creation and response exposes vulnerabilities
class UserModel(BaseModel):
    id: int | None = None
    username: str
    password: str | None = None
    role: str = "user"
```
**Exceptions:** Standalone utility DTOs or independent token responses (`TokenResponse`).  
**Source:** `apps/backend/src/api/schemas/user.py:9-61`.

---

### Rule ID: SCH-003
**Title:** ORM Integration via `from_attributes=True`  
**Priority:** MUST  
**Rule:** All response schemas representing an ORM model **MUST** configure:
```python
model_config = ConfigDict(from_attributes=True)
```
Manual property-by-property mapping (`dto.id = model.id`) **MUST NOT** be used unless custom transformation logic is required.  
**Reason:** Enables Pydantic to read attributes directly from SQLAlchemy model instances via `model_validate(orm_obj)`, eliminating boilerplate code and preventing missed fields.  
**Correct Example:**
```python
class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# In Service:
return UserResponse.model_validate(user_orm)
```
**Incorrect Example:**
```python
# Redundant manual attribute mapping:
return UserResponse(
    id=user_orm.id,
    username=user_orm.username,
    email=user_orm.email,
    role=user_orm.role,
    ...
)
```
**Exceptions:** Dynamically aggregated payloads synthesized across heterogeneous data sources without a single root ORM model.  
**Source:** `apps/backend/src/api/schemas/user.py:60`, `apps/backend/src/api/services/user.py:67`.

---

### Rule ID: SCH-004
**Title:** Sensitive Field Exclusion from Response DTOs  
**Priority:** MUST  
**Rule:** Sensitive fields such as `hashed_password`, `salt`, `secret_key`, and internal session tokens **MUST NEVER** be declared in any outgoing Response schema.  
**Reason:** Eliminates Data Leakage risks even if the repository layer accidentally loads full ORM model entities.  
**Correct Example:**
```python
class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # hashed_password is completely omitted!
```
**Incorrect Example:**
```python
class UserResponse(UserBase):
    id: int
    hashed_password: str  # SEVERE SECURITY VULNERABILITY!
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/schemas/user.py:53-61`.

---

### Rule ID: SCH-005
**Title:** Field Constraints via `Field(...)`  
**Priority:** MUST  
**Rule:** Incoming string and numerical fields **MUST** declare lower bounds (`min_length`, `ge`) and upper bounds (`max_length`, `le`) using `Field(...)`. Email fields **MUST** use the `EmailStr` type (validated via `email-validator`).  
**Reason:** Mitigates Memory Exhaustion and ReDoS attacks caused by massive payloads and validates input consistency before database interaction.  
**Correct Example:**
```python
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["huce_user"])
    email: EmailStr = Field(..., examples=["user@huce.edu.vn"])
    full_name: str | None = Field(None, max_length=100, examples=["Nguyen Van A"])

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="Password minimum 6 characters")
```
**Incorrect Example:**
```python
class UserCreate(BaseModel):
    username: str  # Unconstrained length: allows 10MB strings
    email: str     # Unvalidated format
    password: str  # No minimum length bound
```
**Exceptions:** Boolean flags or bounded enum fields.  
**Source:** `apps/backend/src/api/schemas/user.py:9-19`.

---

### Rule ID: SCH-006
**Title:** Optional Fields Typing Convention  
**Priority:** MUST  
**Rule:** Optional attributes **MUST** be typed using `Type | None = None` or `Field(None, ...)`. Do NOT use `typing.Optional` and do NOT declare `field: Type | None` without the `= None` default (which incorrectly renders the field mandatory with a null value requirement).  
**Reason:** Enforces modern Python 3.12 syntax and prevents clients from being forced to supply `"field": null` in JSON payloads.  
**Correct Example:**
```python
class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=100, examples=["Nguyen Van A"])
```
**Incorrect Example:**
```python
from typing import Optional

class UserUpdate(BaseModel):
    full_name: Optional[str]        # Missing = None -> Becomes a required field!
    bio: str | None                 # Missing = None
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/schemas/user.py:12, 42`.

---

### Rule ID: SCH-007
**Title:** Partial Updates via `exclude_unset=True`  
**Priority:** MUST  
**Rule:** When processing partial update schemas (`PATCH` endpoints), services and repositories **MUST** deserialize DTOs using `payload.model_dump(exclude_unset=True)`.  
**Reason:** Accurately distinguishes between fields **omitted by the client** (retaining their existing database values) and fields **explicitly set to null** (clearing values in the database). Using `exclude_none=True` prevents clients from deliberately setting nullable fields to null.  
**Correct Example:**
```python
# api/services/user.py
async def update_user(self, user_id: int, payload: UserUpdate) -> UserResponse:
    user = await self.user_repo.get_by_id(user_id)
    if not user:
        raise EntityNotFoundException(entity_name="User", entity_id=user_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    updated_user = await self.user_repo.update(user)
    return UserResponse.model_validate(updated_user)
```
**Incorrect Example:**
```python
update_data = payload.model_dump()  # Overwrites omitted fields with None!
```
**Exceptions:** Full replacement `PUT` endpoints.  
**Source:** `apps/backend/src/api/services/user.py:75`.

---

### Rule ID: SCH-008
**Title:** Custom Field Validation via `@field_validator`  
**Priority:** SHOULD  
**Rule:** When complex custom field normalization is required (e.g., lowercase conversion, whitespace trimming, or special format checks), **SHOULD** use the `@field_validator` decorator with `@classmethod`. Use `mode="before"` when operations must precede Pydantic type coercion.  
**Reason:** Encapsulates input normalization within the schema, keeping domain services focused strictly on business logic.  
**Correct Example:**
```python
# api/core/config.py
@field_validator("DEBUG", mode="before")
@classmethod
def parse_debug_env(cls, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on", "debug")
    return bool(value)
```
**Incorrect Example:**
```python
# Parsing logic placed arbitrarily inside route controllers
```
**Exceptions:** Validation requiring database lookups (e.g., verifying username uniqueness) MUST execute in the Service layer, not in Pydantic validators.  
**Source:** `apps/backend/src/api/core/config.py:46-54`.

---

### Rule ID: SCH-009
**Title:** Enum and Literal Value Handling  
**Priority:** SHOULD  
**Rule:** 
- For small, static sets of values (under 5 values), **SHOULD** use `typing.Literal` (e.g., `UserRole = Literal["user", "admin"]`).
- For extensible or complex status sets (e.g., document processing, RAG chunk states), **SHOULD** use `enum.StrEnum` shared between Schemas and ORM Models.  
**Reason:** Generates explicit enum options in Swagger UI and OpenAPI specifications, helping frontend clients recognize valid parameters.  
**Correct Example:**
```python
UserRole = Literal["user", "admin"]

class UserRoleUpdate(BaseModel):
    role: UserRole = Field(..., description="Account role: 'user' or 'admin'")
```
**Incorrect Example:**
```python
class UserRoleUpdate(BaseModel):
    role: str  # Unconstrained string without allowed value restrictions
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/schemas/user.py:6, 49-51`.

---

### Rule ID: SCH-010
**Title:** Schema Organization and Explicit Exports  
**Priority:** MUST  
**Rule:** Schemas for each domain **MUST** reside in `api/schemas/<module>.py` and **MUST** be explicitly exported in `api/schemas/__init__.py` via `__all__`.  
**Reason:** Keeps cross-module imports clean (`from api.schemas.user import UserCreate`), simplifies refactoring, and eliminates circular import cycles.  
**Correct Example:**
```python
# api/schemas/__init__.py
from api.schemas.common import BaseResponse, PaginatedData, PaginationMeta
from api.schemas.user import UserCreate, UserResponse, UserUpdate

__all__ = [
    "BaseResponse",
    "PaginatedData",
    "PaginationMeta",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
]
```
**Incorrect Example:**
```python
# Empty __init__.py or wildcard imports
from api.schemas.user import *
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/schemas/__init__.py`.
