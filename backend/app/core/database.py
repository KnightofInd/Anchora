from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from collections.abc import AsyncGenerator
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from app.config.settings import settings


# Some connection query params (e.g., connect_timeout) are not accepted by asyncpg.connect
# when SQLAlchemy passes them through; sanitize the DATABASE_URL by removing unsupported
# query params to avoid TypeError at engine connect time.
def _sanitize_database_url(url: str) -> str:
    # First, defensively strip any literal connect_timeout=... or sslmode=... fragments
    # This handles odd encodings or multiple occurrences that might slip past parse_qsl.
    if "connect_timeout=" in url or "sslmode=" in url:
        import re

        # Remove occurrences like 'connect_timeout=10&' or '&connect_timeout=10' or final 'connect_timeout=10'
        url = re.sub(r"([&?])connect_timeout=[^&]*&", r"\1", url)
        url = re.sub(r"([&?])connect_timeout=[^&]*$", r"", url)
        # Remove occurrences like 'sslmode=require&' or '&sslmode=require' or final 'sslmode=require'
        url = re.sub(r"([&?])sslmode=[^&]*&", r"\1", url)
        url = re.sub(r"([&?])sslmode=[^&]*$", r"", url)

    parsed = urlparse(url)
    if not parsed.query:
        return url
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    # Remove connect_timeout and sslmode which asyncpg.connect does not accept as keyword arguments
    q.pop("connect_timeout", None)
    q.pop("sslmode", None)
    # Rebuild URL without the removed params
    new_query = urlencode(q, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


_db_url = _sanitize_database_url(settings.DATABASE_URL)
try:
    # Helpful debug during local dev to confirm URL sanitization
    import logging

    logging.getLogger(__name__).debug("Sanitized DATABASE_URL: %s", _db_url)
except Exception:
    pass

engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    # Ensure SSL is requested at the driver level; asyncpg expects 'ssl' kw in connect_args.
    connect_args={"ssl": "require"},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
