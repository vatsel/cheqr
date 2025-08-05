from typing import Optional, AsyncGenerator, Annotated
from contextlib import asynccontextmanager


from fastapi import Depends
from psycopg_pool import AsyncConnectionPool
from psycopg import AsyncConnection

from ..auth.service import get_supabase_conn_str


async def get_test_connection() -> AsyncConnection:
    return await AsyncConnection.connect( await get_supabase_conn_str())


class DatabasePool:
    _pool: Optional[AsyncConnectionPool]

    def __init__(self):
        self._pool = None

    async def init_pool(self):
        if self._pool is not None:

            return

        self._pool = AsyncConnectionPool(
            conninfo= await get_supabase_conn_str(),
            min_size=2,
            max_size=10,
            open=False
        )
        await self._pool.open()

    async def close_pool(self):
        if self._pool:
            await self._pool.close()

    @asynccontextmanager
    async def get_db_conn(self):
        if self._pool is None:
            raise TypeError("Failed to initialise connection pool at startup.")
        
        async with self._pool.connection() as conn:
            yield conn


db = DatabasePool()


async def get_db_conn() -> AsyncGenerator[AsyncConnection, None]:
    async with db.get_db_conn() as conn:
        yield conn



DbConn = Annotated[AsyncConnection, Depends(get_db_conn)]