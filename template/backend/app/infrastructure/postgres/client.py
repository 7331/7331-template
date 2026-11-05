from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.postgres.log_events import DatabaseClosed
from app.shared import logging as log
from app.shared.blocking_executor import BlockingExecutor

logger = log.get_logger(__name__)

ALEMBIC_CONFIGURATION_PATH = Path(__file__).resolve().parents[3] / "alembic.ini"
DATABASE_CONNECT_TIMEOUT_SECONDS = 10
DATABASE_STATEMENT_TIMEOUT_SECONDS = 30
DATABASE_IDLE_IN_TRANSACTION_TIMEOUT_SECONDS = 60
DATABASE_LOCK_TIMEOUT_SECONDS = 15
DATABASE_POOL_TIMEOUT_SECONDS = 30


def read_current_revision(connection: Connection) -> str | None:
    return MigrationContext.configure(connection).get_current_revision()


def read_head_revision() -> str | None:
    return ScriptDirectory.from_config(AlembicConfig(str(ALEMBIC_CONFIGURATION_PATH))).get_current_head()


class Database:
    def __init__(self, dsn: str, *, application_name: str, pool_size: int, maximum_overflow: int) -> None:
        self.engine: AsyncEngine = create_async_engine(
            dsn,
            pool_size=pool_size,
            max_overflow=maximum_overflow,
            pool_timeout=DATABASE_POOL_TIMEOUT_SECONDS,
            pool_pre_ping=True,
            hide_parameters=True,
            connect_args={
                "application_name": application_name,
                "options": (
                    f"-c statement_timeout={DATABASE_STATEMENT_TIMEOUT_SECONDS * 1000} "
                    f"-c idle_in_transaction_session_timeout={DATABASE_IDLE_IN_TRANSACTION_TIMEOUT_SECONDS * 1000} "
                    f"-c lock_timeout={DATABASE_LOCK_TIMEOUT_SECONDS * 1000} "
                    "-c timezone=UTC"
                ),
                "connect_timeout": DATABASE_CONNECT_TIMEOUT_SECONDS,
            },
            execution_options={"isolation_level": "READ COMMITTED"},
        )
        self.session_factory = async_sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)

    async def refuse_schema_behind_head(self, *, file_read_executor: BlockingExecutor) -> None:
        async with self.engine.connect() as connection:
            current_revision = await connection.run_sync(read_current_revision)
        head_revision = await file_read_executor.run_blocking(read_head_revision)
        if current_revision != head_revision:
            raise RuntimeError(
                f"schema is at {current_revision}, this build needs {head_revision}; run `alembic upgrade head`"
            )

    async def close(self) -> None:
        await self.engine.dispose()
        log.emit(logger, event=DatabaseClosed())
