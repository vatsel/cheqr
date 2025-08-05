from datetime import datetime

from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from fastapi import status, HTTPException

from ..user.models import UserData

# TODO: add usage statistics 
# TODO: disable API Docs.

def _one_result_to_user_data_obj(tupleRowResult: TupleRow) -> UserData:
    user_id, email, paid_until, trial_until, created_at, updated_at = tupleRowResult

    return UserData(
        user_id=user_id,
        email=email,
        paid_until=paid_until,
        trial_until=trial_until,
        created_at=created_at,
        updated_at=updated_at
    )


async def get_user_exists(user_id:int, conn:AsyncConnection) -> bool:
    async with conn.cursor() as cur:
        await cur.execute("""
            SELECT id FROM users
            WHERE id = %s
            """, [user_id])
        result = await cur.fetchone()
    
        return result is not None


async def get_user_exists_by_email(user_email:str, conn:AsyncConnection) -> bool:
    async with conn.cursor() as cur:
        await cur.execute("""
            SELECT * FROM users
            WHERE email = %s
            """, [user_email])
        result = await cur.fetchone()
        
        return result is not None


async def get_user_data(user_id:int, conn:AsyncConnection) -> UserData:
    async with conn.cursor() as cur:
        await cur.execute("""
            SELECT * FROM users
            WHERE id = %s
            """, [user_id])
        tupleResult = await cur.fetchone()
        if tupleResult is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No user exists with id {user_id}")
        

        return _one_result_to_user_data_obj(tupleRowResult=tupleResult)


async def get_user_id_by_email(user_email:str, conn:AsyncConnection) -> int:
    async with conn.cursor() as cur:
        await cur.execute("""
            SELECT id FROM users
            WHERE email = %s
            """, [user_email])
        result = await cur.fetchone()
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No user exists with email {user_email}")
        return result[0]


async def get_user_data_from_email(user_email:str, conn:AsyncConnection) -> UserData:
    async with conn.cursor() as cur:
        await cur.execute("""
            SELECT * FROM users
            WHERE email = %s
            """, [user_email])
        result = await cur.fetchone()
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No user exists with email {user_email}")
        
        return _one_result_to_user_data_obj(tupleRowResult=result)
    

async def register_user(user_email:str, conn:AsyncConnection) -> UserData:
    if await get_user_exists_by_email(user_email=user_email, conn=conn):
        detail=(f"User entry already exists for email {user_email}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    
    async with conn.cursor() as cur:
        await cur.execute("""
            INSERT INTO users 
            (email)
            VALUES (%s)
            RETURNING *
            """,[user_email])
        result = await cur.fetchone()
        if result is None:
            raise TypeError(f"failed to register user with result {result}")
        return _one_result_to_user_data_obj(result)
    

async def delete_user(user_id:int, conn:AsyncConnection) -> None:
    async with conn.cursor() as cur:
        await cur.execute("""
            DELETE FROM users
            WHERE id = %s
            """,[user_id])
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No user exists with id {user_id}")


async def extend_user_subscription(user_id:int, payment_until:datetime) -> None:
    raise NotImplementedError("TODO")
