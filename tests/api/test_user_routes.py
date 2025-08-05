from httpx import AsyncClient

import pytest

from tests.constants import VALID_EMAIL, NON_EXISTENT_ID

BASE_URL = "/api/v1/user"

pytestmark = pytest.mark.user

#  ---- POST /register

async def test_register_user_success(client: AsyncClient):
    payload = {"user_email": "new_user@example.com"}

    response = await client.post(f"{BASE_URL}/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] is not None


async def test_register_user_conflict(client: AsyncClient, create_user):
    # Setup: Create user via DB first
    await create_user(email=VALID_EMAIL)

    # Act: Try to register same email via API
    payload = {"user_email": VALID_EMAIL}
    response = await client.post("/api/v1/user/register", json=payload)

    # Assert: 409 Conflict
    assert response.status_code == 409


async def test_delete_user(client:AsyncClient, create_user):
    user_id = await create_user(email=VALID_EMAIL)

    response = await client.delete(f"{BASE_URL}/{user_id}")
    assert response.status_code == 204


#  ---- POST /id-by-email

async def test_get_user_id_by_email_success(client: AsyncClient, create_user):
    expected_id = await create_user(email=VALID_EMAIL)

    response = await client.post(
        f"{BASE_URL}/id-by-email", 
        json={"user_email": VALID_EMAIL}
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == expected_id

async def test_get_user_id_by_email_not_found(client: AsyncClient):
    response = await client.post(
        f"{BASE_URL}/id-by-email", 
        json={"user_email": "ghost@example.com"}
    )
    assert response.status_code == 404


#  ---- POST /data-by-email

async def test_user_data_by_email_success(client: AsyncClient, create_user):
    expected_id = await create_user(email=VALID_EMAIL)

    response = await client.post(
        f"{BASE_URL}/data-by-email", 
        json={"user_email": VALID_EMAIL}
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == expected_id

async def test_user_data_by_email_normalization(client: AsyncClient, create_user):
    """Ensure API handles mixed-case emails."""
    expected_id = await create_user(email="lowercase@example.com")

    # Send UPPERCASE in request
    response = await client.post(
        f"{BASE_URL}/data-by-email", 
        json={"user_email": "LOWERCASE@EXAMPLE.COM"}
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == expected_id

#  ---- GET /{user_id}

async def test_get_user_by_id_success(client: AsyncClient, create_user):
    user_id = await create_user(email=VALID_EMAIL)

    response = await client.get(f"{BASE_URL}/{user_id}")

    assert response.status_code == 200
    assert response.json()["user_id"] == user_id

async def test_get_user_by_id_not_found(client: AsyncClient):
    response = await client.get(f"{BASE_URL}/{NON_EXISTENT_ID}")
    assert response.status_code == 404

#  ---- DELETE /{user_id}

async def test_delete_user_success(client: AsyncClient, create_user):
    user_id = await create_user(email="delete_api@example.com")

    # Act
    response = await client.delete(f"{BASE_URL}/{user_id}")
    assert response.status_code == 204

    # Verify Gone
    check_response = await client.get(f"{BASE_URL}/{user_id}")
    assert check_response.status_code == 404

async def test_delete_user_not_found(client: AsyncClient):
    response = await client.delete(f"{BASE_URL}/{NON_EXISTENT_ID}")
    assert response.status_code == 404


