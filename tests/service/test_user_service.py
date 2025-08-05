import pytest
from psycopg import AsyncConnection
from fastapi import HTTPException, status

from project_context.user.service import (
    register_user, 
    get_user_exists, 
    get_user_data,
    get_user_exists_by_email,
    get_user_id_by_email,
    get_user_data_from_email,
    delete_user
)

from tests.constants import VALID_EMAIL, NON_EXISTENT_ID

pytestmark = pytest.mark.user

#  ----  Tests for get_user_exists (By ID)

async def test_get_user_exists_true(db_conn: AsyncConnection, create_user):
    user_id = await create_user(email=VALID_EMAIL)
    
    result = await get_user_exists(user_id=user_id, conn=db_conn)
    assert result is True


async def test_get_user_exists_false(db_conn: AsyncConnection):
    result = await get_user_exists(user_id=NON_EXISTENT_ID, conn=db_conn)
    assert result is False

#  ----  Tests for get_user_exists_by_email

async def test_get_user_exists_by_email_true(db_conn: AsyncConnection, create_user):
    await create_user(email=VALID_EMAIL)
    
    result = await get_user_exists_by_email(user_email=VALID_EMAIL, conn=db_conn)
    assert result is True

async def test_get_user_exists_by_email_false(db_conn: AsyncConnection):
    result = await get_user_exists_by_email(user_email="ghost@example.com", conn=db_conn)
    assert result is False

#  ----  Tests for get_user_id_by_email

async def test_get_user_id_by_email_success(db_conn: AsyncConnection, create_user):
    created_id = await create_user(email=VALID_EMAIL)
    
    fetched_id = await get_user_id_by_email(user_email=VALID_EMAIL, conn=db_conn)
    assert fetched_id == created_id

async def test_get_user_id_by_email_not_found(db_conn: AsyncConnection):
    with pytest.raises(HTTPException) as exc:
        await get_user_id_by_email(user_email="missing@example.com", conn=db_conn)
    
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


#  ---- Tests for get_user_data_from_email

async def test_get_user_data_from_email_success(db_conn: AsyncConnection, create_user):
    created_id = await create_user(email=VALID_EMAIL)
    
    user_data = await get_user_data_from_email(user_email=VALID_EMAIL, conn=db_conn)
    assert user_data.user_id == created_id

async def test_get_user_data_from_email_not_found(db_conn: AsyncConnection):
    with pytest.raises(HTTPException) as exc:
        await get_user_data_from_email(user_email="missing@example.com", conn=db_conn)
    
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


#  ---- Tests for get_user_data (By ID)

async def test_get_user_data_success(db_conn:AsyncConnection):
    async with db_conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO users (email) VALUES (%s) RETURNING id", 
            [VALID_EMAIL]
        )
        response = await cur.fetchone()
        assert response is not None
        user_id = response[0]

        user = await get_user_data(user_id=user_id, conn=db_conn)
        assert user.user_id == user_id


async def test_get_user_data_not_found(db_conn: AsyncConnection):
    with pytest.raises(HTTPException) as exc_info:
        await get_user_data(user_id=NON_EXISTENT_ID, conn=db_conn)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert f"No user exists with id {NON_EXISTENT_ID}" in exc_info.value.detail


#  ---- Tests for delete_user

async def test_delete_user_success(db_conn: AsyncConnection, create_user):
    user_id = await create_user(email="delete_me@example.com")
    
    await delete_user(user_id=user_id, conn=db_conn)
    
    # Verify deletion
    exists = await get_user_exists(user_id=user_id, conn=db_conn)
    assert exists is False

async def test_delete_user_not_found(db_conn: AsyncConnection):
    with pytest.raises(HTTPException) as exc:
        await delete_user(user_id=NON_EXISTENT_ID, conn=db_conn)
        
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


#  ---- Tests for register_user

async def test_register_user_success(db_conn:AsyncConnection):
    user = await register_user(user_email=VALID_EMAIL, conn=db_conn)

    assert user.email == VALID_EMAIL
    assert user.user_id is not None

    exists = await get_user_exists(user_id=user.user_id, conn=db_conn)
    assert exists is True


