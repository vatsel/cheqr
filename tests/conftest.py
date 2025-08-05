from httpx import AsyncClient, ASGITransport

import pytest_asyncio
from psycopg import AsyncConnection
from tests.constants import VALID_THREAD_ID

from project_context.main import app as main_app
from project_context.postgres.service import get_db_conn, get_test_connection
from project_context.auth.service import get_x_api_access_secret



@pytest_asyncio.fixture
async def db_conn():
    conn = await get_test_connection()

    yield conn

    await conn.rollback()
    await conn.close()


@pytest_asyncio.fixture
async def app(db_conn: AsyncConnection):
    async def mock_commit():
        pass

    db_conn.commit = mock_commit

    async def override_get_db_conn():
        yield db_conn

    main_app.dependency_overrides[get_db_conn] = override_get_db_conn
    yield main_app
    main_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)

    global_headers = {
        "X-API-Key" : await get_x_api_access_secret(),
        "Content-Type": "application/json"
    }

    async with AsyncClient(transport=transport, base_url="http://test", headers=global_headers) as c:
        yield c


@pytest_asyncio.fixture
async def create_user(db_conn: AsyncConnection):
    '''returns a wrapper function. 
    pytest fixtures can only accept other fixtures, not custom args'''

    async def _factory(email:str) -> int:
        async with db_conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO users (email) VALUES (%s) RETURNING id", 
                [email]
            )
            row = await cur.fetchone()
            assert row is not None
            return row[0]
        
    return _factory


@pytest_asyncio.fixture
async def create_project(db_conn: AsyncConnection, create_user):
    '''returns a wrapper function. 
    pytest fixtures can only accept other fixtures, not custom args'''
    async def _factory(thread_id: str = VALID_THREAD_ID):

        generated_email = f"user_for_{thread_id}@example.com"

        user_id = await create_user(email=generated_email)
        
        async with db_conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO projects (user_id) VALUES (%s) RETURNING id", 
                [user_id]
            )
            project_row = await cur.fetchone()
            project_id = project_row[0]

            # 3. Register the Thread ID (Crucial!)
            await cur.execute("""
                INSERT INTO active_gmail_thread_ids 
                (user_id, project_id, gmail_thread_id)
                VALUES (%s, %s, %s)
            """, [user_id, project_id, thread_id])
            
            return project_id, user_id, thread_id

    return _factory