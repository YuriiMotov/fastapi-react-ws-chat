from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

engine = create_async_engine(
    "sqlite+aiosqlite://", connect_args={"check_same_thread": False}
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
