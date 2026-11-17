# HUCE-KMS — Database & ORM Engineering Rules

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: SQLAlchemy 2.0 Async ORM & Database Persistence Guidelines  
> **Scope**: All ORM Models (`api/models/`) and Database Interactions in `apps/backend`  
> **Last Updated**: 2026-11-08  
> **Rule Prefix**: `DB-xxx`

---

## 1. Database Layer Architecture Overview

HUCE-KMS utilizes **SQLAlchemy 2.0** with asynchronous architecture (`asyncio`), powered natively by the `asyncpg` driver connecting to **PostgreSQL 16** (via Docker container `huce-kms-postgres` on port 5432).

Core database architectural components:
1. **Async Engine & Sessionmaker**: Initialized centrally in `api/core/database.py`.
2. **Declarative Base**: Inherits `AsyncAttrs` and `DeclarativeBase` to support asynchronous ORM attribute inspection.
3. **TimestampMixin**: Automates UTC timezone-aware `created_at` and `updated_at` tracking.
4. **Request-Scoped Unit of Work (Transaction Lifecycle)**: Managed by the `get_db_session` dependency—commits on success, rolls back on error, and closes connections in the `finally` block.

---

## 2. Database Rules Catalog

### Rule ID: DB-001
**Title:** Mandatory Modern SQLAlchemy 2.0 Syntax (`Mapped` & `mapped_column`)  
**Priority:** MUST  
**Rule:** All ORM model attributes **MUST** be declared using SQLAlchemy 2.0 type-annotated syntax:
```python
field_name: Mapped[PythonType] = mapped_column(SQLAlchemyType, ...)
```
Legacy SQLAlchemy 1.x declarations such as `Column(Integer, ...)` or untyped declarations without `Mapped[...]` are **STRICTLY FORBIDDEN**.  
**Reason:** 2.0 syntax leverages static type checking (Mypy, Pyright), provides automatic Python type inference, and eliminates runtime typing defects.  
**Correct Example:**
```python
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from api.core.database import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```
**Incorrect Example:**
```python
from sqlalchemy import Column, Integer, String

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)      # Legacy 1.x syntax
    username = Column(String(50), unique=True)  # Missing Mapped annotation
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/models/user.py:16-22`, `apps/backend/src/api/models/refresh_token.py:17-29`.

---

### Rule ID: DB-002
**Title:** Mandatory Inheritance from `Base` and `TimestampMixin`  
**Priority:** MUST  
**Rule:** All ORM Models representing database tables **MUST** inherit from `Base` and **SHOULD** inherit from `TimestampMixin` (providing `created_at` and `updated_at` using `DateTime(timezone=True)` with `server_default=func.now()`).  
**Reason:** Standardizes audit history across all tables and guarantees that `Base.metadata` collects complete table metadata for startup initialization and Alembic migrations.  
**Correct Example:**
```python
# api/core/database.py
class Base(AsyncAttrs, DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

# Model
class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"
    ...
```
**Incorrect Example:**
```python
class RefreshToken(Base):  # Missing TimestampMixin
    __tablename__ = "refresh_tokens"
    created_at = Column(DateTime) # Manual datetime declaration missing timezone and defaults
```
**Exceptions:** Pure many-to-many associative link tables without domain identity MAY inherit solely from `Base`.  
**Source:** `apps/backend/src/api/core/database.py:30-49`.

---

### Rule ID: DB-003
**Title:** Primary Key and Indexing Conventions  
**Priority:** MUST  
**Rule:** 
- The standard primary key **MUST** be a time-ordered 128-bit UUIDv7 (PostgreSQL native `uuid` type):
  `id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7, index=True)`.
- Fields frequently used in query `WHERE` clauses (e.g., `username`, `email`, `token_hash`, `user_id`, `expires_at`, `is_revoked`) **MUST** be indexed using `index=True` or an explicit `Index(...)` declaration.
- Fields requiring uniqueness across the database **MUST** declare `unique=True`.  
**Reason:** UUIDv7 provides non-enumerable, globally unique IDs while preserving B-Tree index locality and sequential insertion performance without index fragmentation.  
**Correct Example:**
```python
from uuid import UUID
from sqlalchemy import String, Uuid, ForeignKey
from api.core.database import Base, TimestampMixin, uuid7

class User(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
```
**Incorrect Example:**
```python
id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # Deprecated auto-increment int
```
**Exceptions:** None. All primary keys and referencing foreign keys standardize on UUIDv7.  
**Source:** `apps/backend/src/api/models/user.py`, `apps/backend/src/api/models/refresh_token.py`.

---

### Rule ID: DB-004
**Title:** Foreign Key Constraints and Cascade Deletion  
**Priority:** MUST  
**Rule:** All foreign key columns **MUST** declare an explicit `ondelete` constraint (typically `"CASCADE"` or `"SET NULL"`):
```python
user_id: Mapped[int] = mapped_column(
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)
```
The corresponding parent model relationship **MUST** specify `cascade="all, delete-orphan"`.  
**Reason:** Preserves referential integrity and prevents orphaned records when parent entities are deleted.  
**Correct Example:**
```python
# Parent Model (User)
refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
    back_populates="user",
    cascade="all, delete-orphan",
)

# Child Model (RefreshToken)
user_id: Mapped[int] = mapped_column(
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)
user: Mapped["User"] = relationship(back_populates="refresh_tokens")
```
**Incorrect Example:**
```python
user_id: Mapped[int] = mapped_column(ForeignKey("users.id")) # Missing ondelete="CASCADE"
```
**Exceptions:** Audit logs and historical tracking tables where the record must persist after user deletion SHOULD use `ondelete="SET NULL"` with `nullable=True`.  
**Source:** `apps/backend/src/api/models/user.py:25-28`, `apps/backend/src/api/models/refresh_token.py:19-23`.

---

### Rule ID: DB-005
**Title:** Relationship Declarations via Forward References and `back_populates`  
**Priority:** MUST  
**Rule:** `relationship` attributes **MUST** reference the target Model via a string forward reference (e.g., `"RefreshToken"`) combined with `TYPE_CHECKING` guards, and **MUST** be declared bidirectionally using `back_populates`. Deprecated `backref` syntax **MUST NOT** be used.  
**Reason:** Prevents circular import errors between model modules and makes relationships explicit on both ends.  
**Correct Example:**
```python
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from api.models.refresh_token import RefreshToken

class User(Base, TimestampMixin):
    ...
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
```
**Incorrect Example:**
```python
from api.models.refresh_token import RefreshToken # Direct import causes circular dependency

class User(Base):
    refresh_tokens = relationship("RefreshToken", backref="user") # Legacy backref
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/models/user.py:1, 7-9, 25-28`.

---

### Rule ID: DB-006
**Title:** Modern Query Execution via `select()` and Scalars  
**Priority:** MUST  
**Rule:** All database read operations **MUST** use `select(Model)` with `await session.execute(...)`:
- Single record or None: `result.scalar_one_or_none()`.
- Single scalar value (e.g., count): `result.scalar_one()`.
- Multiple record list: `result.scalars().all()`.
- Legacy `session.query(...)` **MUST NOT** be used.  
**Reason:** Ensures full compatibility with SQLAlchemy 2.0 Asyncio and cleanly separates SQL statement building from execution.  
**Correct Example:**
```python
# Single record
stmt = select(User).where(User.username == username)
result = await self.session.execute(stmt)
user = result.scalar_one_or_none()

# Multiple records
stmt = select(User).offset(skip).limit(limit).order_by(User.id.desc())
result = await self.session.execute(stmt)
users = result.scalars().all()

# Count query
count_stmt = select(func.count(User.id))
count_result = await self.session.execute(count_stmt)
total = count_result.scalar_one()
```
**Incorrect Example:**
```python
user = await session.query(User).filter_by(username=username).first() # Incompatible with async
```
**Exceptions:** Simple primary key lookups MAY use the shorthand method `await session.get(Model, id)`.  
**Source:** `apps/backend/src/api/repositories/user.py:16-18, 48-50, 60-62`, `apps/backend/src/api/repositories/base.py:20`.

---

### Rule ID: DB-007
**Title:** Eager Loading in Asynchronous Contexts (N+1 Prevention)  
**Priority:** MUST  
**Rule:** In async environments, implicit lazy loading is disabled and will trigger a fatal `greenlet_spawn has not been called` runtime error. When accessing relationship attributes, developers **MUST** eager-load them explicitly:
- One-to-Many or Many-to-Many: Use `selectinload(Model.relationship_name)`.
- One-to-One or Many-to-One: Use `joinedload(Model.relationship_name)`.  
**Reason:** Prevents async runtime crashes and eliminates N+1 query bottlenecks.  
**Correct Example:**
```python
from sqlalchemy.orm import selectinload

# Eager-load User with all their refresh_tokens in a single round-trip
stmt = select(User).where(User.id == user_id).options(selectinload(User.refresh_tokens))
result = await self.session.execute(stmt)
user = result.scalar_one_or_none()
```
**Incorrect Example:**
```python
stmt = select(User).where(User.id == user_id)
result = await self.session.execute(stmt)
user = result.scalar_one_or_none()

# Accessing unloaded relationship attribute in async triggers a Greenlet error crash!
tokens = user.refresh_tokens 
```
**Exceptions:** When an endpoint only accesses columns on the root model and does not touch relationship attributes.  
**Source:** Core Async SQLAlchemy 2.0 design (enforced for upcoming Document & Chunks modules).

---

### Rule ID: DB-008
**Title:** Transaction Boundaries and Flush-Only Rule in Repositories  
**Priority:** MUST  
**Rule:** Across all Repository classes (`BaseRepository`, `UserRepository`, etc.), persistence methods **MUST ONLY** call `await self.session.flush()` and `await self.session.refresh(instance)`. Repositories **MUST NEVER** call `await self.session.commit()`. Commits and rollbacks are exclusively controlled by the `get_db_session` dependency.  
**Reason:** Allows multiple repository actions to be combined into a single atomic Unit of Work. If an error occurs midway, all preceding operations roll back cleanly.  
**Correct Example:**
```python
# api/repositories/base.py
async def create(self, instance: ModelType) -> ModelType:
    self.session.add(instance)
    await self.session.flush()
    await self.session.refresh(instance)
    return instance

async def update(self, instance: ModelType) -> ModelType:
    await self.session.flush()
    await self.session.refresh(instance)
    return instance
```
**Incorrect Example:**
```python
async def create(self, instance: ModelType) -> ModelType:
    self.session.add(instance)
    await self.session.commit() # VIOLATION: Manual commit breaks the outer request transaction
    return instance
```
**Exceptions:** Independent background tasks or CLI scripts running completely outside the FastAPI request lifecycle.  
**Source:** `apps/backend/src/api/repositories/base.py:28-44`, `apps/backend/src/api/core/dependencies.py:47-54`.

---

### Rule ID: DB-009
**Title:** PostgreSQL Connection & Docker Environment Management  
**Priority:** MUST  
**Rule:** During development and deployment, developers **MUST** observe:
1. The database connection MUST use the asynchronous driver `postgresql+asyncpg://`. Synchronous drivers (`psycopg2`) are strictly forbidden.
2. Connection configuration is loaded from `.env` via `settings.DATABASE_URL`.
3. PostgreSQL runs inside Docker container `huce-kms-postgres` defined in the root `docker-compose.yml`. SQLite is deprecated and deleted.  
**Reason:** Ensures consistent relational database behavior between local development, staging, and production environments, eliminating dialect discrepancies.  
**Correct Example:**
```python
# api/core/config.py
DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/huce_kms"
```
**Incorrect Example:**
```python
DATABASE_URL: str = "sqlite+aiosqlite:///huce_kms.db" # Deprecated legacy SQLite
```
**Exceptions:** None.  
**Source:** `apps/backend/src/api/core/config.py:32`, `docker-compose.yml`.

---

### Rule ID: DB-010
**Title:** Alembic Database Migration Strategy  
**Priority:** SHOULD  
**Rule:** 
- All database model modifications (adding columns, altering types, creating tables) **SHOULD** be applied to model classes in `api/models/` first, followed by the generation of a corresponding migration script.
- In the active development environment, `Base.metadata.create_all` in `lifespan.py` initializes tables automatically. For staging and production environments, the migration workflow **SHOULD** transition to:
  ```bash
  uv run alembic revision --autogenerate -m "<description>"
  uv run alembic upgrade head
  ```
- `migrations/env.py` is pre-configured with an async runner bound to `target_metadata = Base.metadata`.  
**Reason:** Ensures database schema evolution is version-controlled in Git, enabling reliable rollback during deployment failures.  
**Correct Example:**
```python
# migrations/env.py
from api.models import Base
target_metadata = Base.metadata
```
**Incorrect Example:**
```sql
-- Manually running ALTER TABLE against the database without model updates and migration files
```
**Exceptions:** None.  
**Source:** `apps/backend/migrations/env.py:27`, `apps/backend/src/api/core/lifespan.py:62-64`.
