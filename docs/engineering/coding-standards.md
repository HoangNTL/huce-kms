# HUCE-KMS — Backend Coding Standards & Engineering Guidelines

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: Backend Coding Standards & Engineering Guidelines  
> **Scope**: All engineers and AI Coding Agents developing in `apps/backend`  
> **Last Updated**: 2026-11-08  

Normative Classification:
- **MUST**: Absolute requirement. Violations must be rejected during code review.
- **SHOULD**: Strong recommendation. Can only be bypassed with explicit technical justification.
- **MAY**: Optional, applied contextually to improve clarity.

---

## 1. Python Version & Language Features

### 1.1. Minimum Python Version (MUST)
- **Rule**: All backend source code **MUST** be compatible with Python `>= 3.12`.
- **Rationale**: The project uses the Python 3.12 runtime (`.python-version: 3.12`, `pyproject.toml: requires-python = ">=3.12"`).

### 1.2. Modern Union Syntax (MUST)
- **Rule**: **MUST** use the `|` operator for Union and Optional types. Do NOT import or use `typing.Union` or `typing.Optional`.
- **Correct**:
  ```python
  def get_user(user_id: int, note: str | None = None) -> User | None:
      ...
  ```
- **Incorrect**:
  ```python
  from typing import Optional, Union
  def get_user(user_id: int, note: Optional[str] = None) -> Union[User, None]:
      ...
  ```

### 1.3. Standard Built-in Collections for Typing (MUST)
- **Rule**: **MUST** use built-in collection types `list`, `dict`, `set`, and `tuple` for type annotations. Do NOT import `List`, `Dict`, `Set`, or `Tuple` from `typing`.
- **Correct**:
  ```python
  tags: list[str] = []
  metadata: dict[str, str] = {}
  ```
- **Incorrect**:
  ```python
  from typing import List, Dict
  tags: List[str] = []
  ```

---

## 2. Async / Await Conventions

### 2.1. Non-blocking I/O (MUST)
- **Rule**: All I/O operations (Database, Network, Filesystem) **MUST** be asynchronous and preceded by `await`. Blocking I/O libraries (e.g., `requests`, `urllib`, `time.sleep`) **MUST NOT** be called inside async handlers.
- **Correct**:
  ```python
  import asyncio
  await asyncio.sleep(1)
  # Database queries
  result = await session.execute(stmt)
  ```
- **Incorrect**:
  ```python
  import time
  time.sleep(1)  # Blocks the server event loop!
  ```

### 2.2. Async Service and Repository Declarations (MUST)
- **Rule**: All functions in Route Handlers, Services, Repositories, and Database dependencies **MUST** be declared with `async def`.

---

## 3. Type Annotations

### 3.1. Comprehensive Function Typing (MUST)
- **Rule**: All functions and methods **MUST** specify explicit type hints for all parameters and return values (`-> ReturnType`).
- **Correct**:
  ```python
  async def get_by_username(self, username: str) -> User | None:
      stmt = select(User).where(User.username == username)
      result = await self.session.execute(stmt)
      return result.scalar_one_or_none()
  ```
- **Incorrect**:
  ```python
  async def get_by_username(self, username):
      stmt = select(User).where(User.username == username)
      result = await self.session.execute(stmt)
      return result.scalar_one_or_none()
  ```

### 3.2. Abstract Collection Types via `collections.abc` (SHOULD)
- **Rule**: **SHOULD** import abstract collection interfaces (`Sequence`, `AsyncGenerator`, `Callable`, `Iterable`) from `collections.abc` rather than `typing`.
- **Correct**:
  ```python
  from collections.abc import Sequence, AsyncGenerator
  async def list(self) -> Sequence[User]:
      ...
  ```

---

## 4. Pydantic V2 Conventions

### 4.1. Standard Pydantic V2 Syntax (MUST)
- **Rule**: **MUST** use `ConfigDict` and V2 serialization methods (`model_validate`, `model_dump`). Deprecated V1 syntax (e.g., `class Config`, `parse_obj`, `from_orm`, `dict()`) **MUST NOT** be used.
- **Correct**:
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
- **Incorrect**:
  ```python
  class UserResponse(BaseModel):
      id: int
      username: str

      class Config:
          orm_mode = True

  dto = UserResponse.from_orm(orm_user)  # V1 Deprecated
  ```

### 4.2. Field Constraints via `Field(...)` (SHOULD)
- **Rule**: Input schema attributes subject to bounds or formatting constraints **SHOULD** be declared using `Field` with explicit constraints: `min_length`, `max_length`, `ge`, `le`, `description`, `examples`.
- **Correct**:
  ```python
  username: str = Field(..., min_length=3, max_length=50, examples=["huce_admin"])
  ```

---

## 5. SQLAlchemy 2.0 Conventions

### 5.1. ORM Column Declarations via `Mapped` & `mapped_column` (MUST)
- **Rule**: All ORM Models **MUST** use SQLAlchemy 2.0 declarative syntax: `Mapped[type] = mapped_column(...)`. Legacy 1.x syntax `Column(Type, ...)` **MUST NOT** be used.
- **Correct**:
  ```python
  class User(Base, TimestampMixin):
      __tablename__ = "users"

      id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
      username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
      is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
  ```
- **Incorrect**:
  ```python
  class User(Base):
      __tablename__ = "users"
      id = Column(Integer, primary_key=True)
      username = Column(String(50))
  ```

### 5.2. ORM Relationship Declarations (MUST)
- **Rule**: Relationships **MUST** use `relationship` with forward-referenced string annotations or `TYPE_CHECKING` guards to prevent circular import loops:
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

### 5.3. Standard `select()` Query Execution (MUST)
- **Rule**: All queries **MUST** be constructed using `select(Model)`. Use:
  - `result.scalar_one_or_none()` when retrieving at most one record or None.
  - `result.scalar_one()` when retrieving exactly one record (e.g., `func.count()`).
  - `result.scalars().all()` when retrieving multiple records.
  - Legacy `session.query(Model)` syntax **MUST NOT** be used.
- **Correct**:
  ```python
  stmt = select(User).where(User.username == username)
  result = await self.session.execute(stmt)
  user = result.scalar_one_or_none()
  ```
- **Incorrect**:
  ```python
  user = self.session.query(User).filter_by(username=username).first()  # Legacy 1.x
  ```

### 5.4. Flush vs. Commit in Repositories (MUST)
- **Rule**: Inside `BaseRepository` and derived repository classes, **MUST** only call `await self.session.flush()` and `await self.session.refresh(instance)`. Repositories **MUST NEVER** call `await self.session.commit()`. Committing transactions is the exclusive responsibility of the request lifecycle dependency (`get_db_session`).

---

## 6. Imports & Code Organization

### 6.1. Import Ordering (MUST)
- **Rule**: Imports **MUST** be organized into three distinct groups separated by a single blank line:
  1. Python Standard Library (`collections.abc`, `datetime`, `pathlib`, `typing`, `uuid`).
  2. Third-party packages (FastAPI, SQLAlchemy, Pydantic, PyJWT, pwdlib).
  3. First-party internal project modules prefixed with `api.*`.
- **Correct**:
  ```python
  # 1. Standard library
  from datetime import datetime, timezone
  from typing import Annotated

  # 2. Third-party packages
  from fastapi import APIRouter, Depends, status
  from sqlalchemy.ext.asyncio import AsyncSession

  # 3. First-party internal imports
  from api.core.dependencies import DatabaseDep
  from api.schemas.common import BaseResponse
  from api.services.user import UserService
  ```

### 6.2. Wildcard Imports Prohibition (MUST)
- **Rule**: Do NOT use wildcard imports (`from module import *`). Always import classes and functions explicitly.

---

## 7. Error & Exception Handling

### 7.1. Custom `AppException` Hierarchy (MUST)
- **Rule**: Inside Services and Dependencies, domain errors **MUST** be raised using subclasses of `AppException` (defined in `api.core.exceptions`):
  - `EntityNotFoundException`: HTTP 404 when a resource does not exist.
  - `BadRequestException`: HTTP 400 when input data violates business logic.
  - `UnauthorizedException`: HTTP 401 when authentication fails or tokens are invalid.
  - `ForbiddenException`: HTTP 403 when permissions are insufficient.
  - `ConflictException`: HTTP 409 when resources conflict (e.g., duplicate username or email).
- **Correct**:
  ```python
  if existing_user:
      raise ConflictException(message=f"Username '{payload.username}' is already taken.")
  ```
- **Incorrect**:
  ```python
  if existing_user:
      return {"error": "Username taken"}  # Do NOT return error dictionaries
      # or
      raise HTTPException(status_code=400, detail="Username taken")  # Do NOT raise HTTPException in services
  ```

---

## 8. Logging Standards

### 8.1. Named Loggers (MUST)
- **Rule**: **MUST** obtain loggers using `logging.getLogger("huce_kms.<module>")`. `print()` **MUST NOT** be used in backend code.
- **Correct**:
  ```python
  import logging
  logger = logging.getLogger("huce_kms.auth")

  logger.info("User registered successfully: username='%s'", user.username)
  logger.warning("Token reuse detected for user_id=%d", user.id)
  ```
- **Incorrect**:
  ```python
  print(f"User registered: {user.username}")  # print statements are forbidden
  ```

---

## 9. Dependency Injection

### 9.1. Typed Dependency Aliases with `Annotated` (MUST)
- **Rule**: Declare dependencies using `Annotated[Type, Depends(factory)]`.
- **Correct**:
  ```python
  CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
  DatabaseDep = Annotated[AsyncSession, Depends(get_db_session)]
  ```

### 9.2. Route Module Dependency Factory Functions (MUST)
- **Rule**: Each route module **MUST** define a factory function initializing its corresponding Service, injecting `DatabaseDep` and instantiating repositories in the constructor.
- **Correct**:
  ```python
  def get_user_service(db: DatabaseDep) -> UserService:
      user_repo = UserRepository(db)
      refresh_token_repo = RefreshTokenRepository(db)
      return UserService(user_repo, refresh_token_repo)

  UserServiceDep = Annotated[UserService, Depends(get_user_service)]
  ```

---

## 10. Documentation & Docstrings

### 10.1. Class & Method Docstrings (SHOULD)
- **Rule**: Service classes, primary public methods, and complex repository queries **SHOULD** include docstrings explaining purpose, parameters, and return types.

---

## 11. Testing Status & Future Recommendations

### 11.1. Current State
- The `tests/` directory currently does not exist in `apps/backend`.
- Test runners (`pytest`, `pytest-asyncio`, `httpx`) are not yet installed in `pyproject.toml`.

### 11.2. Technical Recommendations for Future Test Phases
- When automated testing is implemented in subsequent phases, the project **SHOULD**:
  1. Add `pytest`, `pytest-asyncio`, and `httpx` to dev dependencies via `uv add --dev pytest pytest-asyncio httpx`.
  2. Create `tests/` with `conftest.py` setting up an asynchronous test client and an in-memory SQLite database.
  3. Name test files `test_<module>.py` and test functions `test_<action>_<expected_result>()`.
