from app.database import models  # noqa: F401
from app.database.base import Base


def test_required_tables_are_registered() -> None:
    required = {
        "users",
        "conversations",
        "messages",
        "projects",
        "goals",
        "tasks",
        "task_dependencies",
        "tool_definitions",
        "tool_executions",
        "permissions",
        "approvals",
        "memories",
        "memory_embeddings",
        "documents",
        "notifications",
        "scheduled_jobs",
        "agent_runs",
        "audit_logs",
        "integrations",
    }
    assert required <= set(Base.metadata.tables)


def test_every_table_has_a_primary_key() -> None:
    for table in Base.metadata.sorted_tables:
        assert table.primary_key.columns, f"{table.name} has no primary key"
