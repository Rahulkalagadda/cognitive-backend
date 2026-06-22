from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Create async engine with standard connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

# Set up the async session local class
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """Dependency generator yielding db transactions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Implicit commit if no error occurs
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
