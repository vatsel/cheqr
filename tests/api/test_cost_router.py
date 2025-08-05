from httpx import AsyncClient
import pytest

from psycopg import AsyncConnection

BASE_URL = "/api/v1/costs"

pytestmark = pytest.mark.cost


# -----------------------------------------------------------------------------
# Helper: Insert Cost via DB (Shared logic)
# -----------------------------------------------------------------------------
async def create_dummy_cost_db(conn: AsyncConnection, user_id: int, project_id: int) -> int:
    async with conn.cursor() as cur:
        await cur.execute("""
            INSERT INTO logged_costs 
            (currency_code, type_code, amount, user_id, project_id, description)
            VALUES ('USD', 'ANTHROPIC_API_CALL', 100.00, %s, %s, 'test desc')
            RETURNING id
        """, (user_id, project_id))
        row = await cur.fetchone()
        return row[0]

# -----------------------------------------------------------------------------
# 1. POST /create
# -----------------------------------------------------------------------------
async def test_create_cost_endpoint(client: AsyncClient, create_project):
    # Setup: Create User/Project first
    pid, uid, _ = await create_project()

    payload = {
        "currency": "USD",
        "amount": 250.75,
        "cost_type": "ANTHROPIC_API_CALL",
        "description": "New Laptop",
        "user_id": uid,
        "project_id": pid
    }

    response = await client.post(f"{BASE_URL}/create", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["cost_id"] is not None

# -----------------------------------------------------------------------------
# 2. GET /{cost_id}
# -----------------------------------------------------------------------------
async def test_get_cost_endpoint_success(client: AsyncClient, db_conn: AsyncConnection, create_project):
    pid, uid, _ = await create_project()
    cost_id = await create_dummy_cost_db(db_conn, uid, pid)

    response = await client.get(f"{BASE_URL}/{cost_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["cost_id"] == cost_id
    assert float(data["amount"]) == 100.00 # From helper

async def test_get_cost_endpoint_404(client: AsyncClient):
    response = await client.get(f"{BASE_URL}/999999")
    assert response.status_code == 404

# -----------------------------------------------------------------------------
# 3. POST /in-usd (Get cost as USD)
# -----------------------------------------------------------------------------
async def test_get_usd_cost_endpoint(client: AsyncClient, db_conn: AsyncConnection, create_project):
    pid, uid, _ = await create_project()
    cost_id = await create_dummy_cost_db(db_conn, uid, pid)

    # Note: Endpoint expects CostIdRequest body
    payload = {"cost_id": cost_id}
    
    response = await client.post(f"{BASE_URL}/in-usd", json=payload)

    assert response.status_code == 200
    assert response.json()["usd_cost"] == 100.0

# -----------------------------------------------------------------------------
# 4. POST /user-totals
# -----------------------------------------------------------------------------
async def test_user_totals_endpoint(client: AsyncClient, db_conn: AsyncConnection, create_project):
    pid, uid, _ = await create_project()
    await create_dummy_cost_db(db_conn, uid, pid) # Cost 1
    await create_dummy_cost_db(db_conn, uid, pid) # Cost 2

    payload = {"user_id": uid}
    
    response = await client.post(f"{BASE_URL}/user-totals", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == uid
    assert len(data["costs"]) == 2

async def test_user_totals_endpoint_404(client: AsyncClient, create_project):
    # User exists but has no costs
    _, uid, _ = await create_project()
    
    payload = {"user_id": uid}
    response = await client.post(f"{BASE_URL}/user-totals", json=payload)
    
    assert response.status_code == 404

# -----------------------------------------------------------------------------
# 5. DELETE /{cost_id}
# -----------------------------------------------------------------------------
async def test_delete_cost_endpoint(client: AsyncClient, db_conn: AsyncConnection, create_project):
    pid, uid, _ = await create_project()
    cost_id = await create_dummy_cost_db(db_conn, uid, pid)

    response = await client.delete(f"{BASE_URL}/{cost_id}")
    
    assert response.status_code == 204

    # Verify Gone
    check = await client.get(f"{BASE_URL}/{cost_id}")
    assert check.status_code == 404