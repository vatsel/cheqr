from decimal import Decimal

import pytest
from fastapi import HTTPException, status
from psycopg import AsyncConnection

from project_context.costs.models import Currency, LoggedCostType
from project_context.costs.schemas import CreateNewCostRequest

# Import Service Functions
from project_context.costs.service import (
    create_cost,
    get_cost_by_id,
    get_cost_in_usd,
    query_all_user_cost_totals,
    delete_cost
)


pytestmark = pytest.mark.cost


# -----------------------------------------------------------------------------
# Helper: Create Cost directly in DB (to isolate Retrieval tests from Create logic)
# -----------------------------------------------------------------------------
async def create_dummy_cost_db(conn: AsyncConnection, 
                               user_id: int, 
                               project_id: int, 
                               amount: float = 100.00) -> int:
    """Inserts a cost via raw SQL and returns the ID."""
    async with conn.cursor() as cur:
        # Note: We must match the columns in your DB. 
        # Assuming 'description' is nullable or handled by DB default based on your provided service code
        await cur.execute("""
            INSERT INTO logged_costs 
            (currency_code, type_code, amount, user_id, project_id, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, ('USD', 'ANTHROPIC_API_CALL', amount, user_id, project_id, 'test desc'))
        row = await cur.fetchone()
        return row[0]

# -----------------------------------------------------------------------------
# 1. Create Cost
# -----------------------------------------------------------------------------
async def test_create_cost_success(db_conn: AsyncConnection, create_project):
    # Setup: We need valid FKs (User & Project)
    pid, uid, _ = await create_project()

    payload = CreateNewCostRequest(
        currency=Currency.USD,
        amount=150.50,
        cost_type=LoggedCostType.ANTHROPIC_API_CALL,
        description="Anthropic API CALL",
        user_id=uid,
        project_id=pid
    )

    # Act
    result = await create_cost(cost_data=payload, conn=db_conn)

    # Assert
    assert result.cost_id is not None
    assert result.amount == Decimal("150.50")
    assert result.user_id == uid
    assert result.project_id == pid

# -----------------------------------------------------------------------------
# 2. Get Cost By ID
# -----------------------------------------------------------------------------
async def test_get_cost_by_id_success(db_conn: AsyncConnection, create_project):
    pid, uid, _ = await create_project()
    cost_id = await create_dummy_cost_db(db_conn, uid, pid, amount=99.99)

    # Act
    cost = await get_cost_by_id(cost_id=cost_id, conn=db_conn)

    # Assert
    assert cost.cost_id == cost_id
    assert cost.amount == Decimal("99.99")

async def test_get_cost_by_id_not_found(db_conn: AsyncConnection):
    with pytest.raises(HTTPException) as exc:
        await get_cost_by_id(cost_id=999999, conn=db_conn)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

# -----------------------------------------------------------------------------
# 3. Get Cost in USD
# -----------------------------------------------------------------------------
async def test_get_cost_in_usd_success(db_conn: AsyncConnection, create_project):
    pid, uid, _ = await create_project()
    cost_id = await create_dummy_cost_db(db_conn, uid, pid, amount=50.00)

    # Act
    usd_val = await get_cost_in_usd(cost_id=cost_id, conn=db_conn)

    # Assert
    assert usd_val == 50.0

async def test_get_cost_in_usd_not_found(db_conn: AsyncConnection):
    with pytest.raises(HTTPException) as exc:
        await get_cost_in_usd(cost_id=999999, conn=db_conn)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

# -----------------------------------------------------------------------------
# 4. Query User Totals
# -----------------------------------------------------------------------------
async def test_query_user_totals_success(db_conn: AsyncConnection, create_project):
    pid, uid, _ = await create_project()
    # Create 2 costs for this user
    await create_dummy_cost_db(db_conn, uid, pid, amount=10.00)
    await create_dummy_cost_db(db_conn, uid, pid, amount=20.00)

    # Act
    response = await query_all_user_cost_totals(user_id=uid, conn=db_conn)

    # Assert
    assert response.user_id == uid
    assert len(response.costs) == 2
    # Optional: Verify sum logic if relevant, or just presence
    amounts = [c.amount for c in response.costs]
    assert Decimal("10.00") in amounts
    assert Decimal("20.00") in amounts
    

async def test_query_user_totals_empty(db_conn: AsyncConnection, create_project):
    # Create user with NO costs
    _, uid, _ = await create_project()

    with pytest.raises(HTTPException) as exc:
        await query_all_user_cost_totals(user_id=uid, conn=db_conn)
    
    # Your service raises 404 if list is empty
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

# -----------------------------------------------------------------------------
# 5. Delete Cost
# -----------------------------------------------------------------------------
async def test_delete_cost_success(db_conn: AsyncConnection, create_project):
    pid, uid, _ = await create_project()
    cost_id = await create_dummy_cost_db(db_conn, uid, pid)

    # Act
    await delete_cost(cost_id=cost_id, conn=db_conn)

    # Assert (Ensure it's gone)
    with pytest.raises(HTTPException) as exc:
        await get_cost_by_id(cost_id=cost_id, conn=db_conn)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

async def test_delete_cost_not_found(db_conn: AsyncConnection):
    with pytest.raises(HTTPException) as exc:
        await delete_cost(cost_id=999999, conn=db_conn)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND