from collections.abc import Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base
from app.database.models import Project, Task, User


class Repository[ModelT: Base]:
    """Small transaction-neutral repository; services own commit boundaries."""

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def get(self, entity_id: UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity


class UserScopedRepository[ModelT: Base](Repository[ModelT]):
    """Base for repositories whose reads must always be tenant scoped."""

    async def get_for_user(self, entity_id: UUID, user_id: UUID) -> ModelT | None:
        statement = select(self.model).where(
            self.model.id == entity_id,  # type: ignore[attr-defined]
            self.model.user_id == user_id,  # type: ignore[attr-defined]
        )
        return cast(ModelT | None, await self.session.scalar(statement))

    async def list_for_user(self, user_id: UUID, *, limit: int = 100) -> Sequence[ModelT]:
        statement: Select[tuple[ModelT]] = (
            select(self.model)
            .where(self.model.user_id == user_id)  # type: ignore[attr-defined]
            .limit(min(max(limit, 1), 500))
        )
        result = await self.session.scalars(statement)
        return result.all()


class UserRepository(Repository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        return cast(
            User | None,
            await self.session.scalar(select(User).where(User.email == email.lower())),
        )


class ProjectRepository(UserScopedRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)


class TaskRepository(Repository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Task)

    async def lock(self, task_id: UUID) -> Task | None:
        """Lock a task before a worker attempts a state transition."""

        return cast(
            Task | None,
            await self.session.scalar(
                select(Task).where(Task.id == task_id).with_for_update(skip_locked=True)
            ),
        )
