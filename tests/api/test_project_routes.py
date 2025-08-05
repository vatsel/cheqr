import pytest
from unittest.mock import patch
from httpx import AsyncClient
from project_context.ai.models import ParsedAIResponse
from tests.constants import DUMMY_MSG_PAYLOAD, VALID_EMAIL

BASE_URL = "/api/v1/project"

pytestmark = pytest.mark.project



# ----- POST /create

async def test_create_project_endpoint(client: AsyncClient, create_user):
    # Create user first via DB helper
    user_id = await create_user(email=VALID_EMAIL)
    
    payload = {
        "user_id": user_id,
        "thread_id": "thread-api-create"
    }

    response = await client.post(f"{BASE_URL}/create", json=payload)
    
    assert response.status_code == 201
    assert response.json()["project_id"] is not None


# ----- POST /create-from-thread (Integration)

async def test_create_from_thread_endpoint(client: AsyncClient, create_user):
    """Tests creating AND processing comms in one go."""
    user_id = await create_user(email="api_full@example.com")
    
    payload = {
        "user_id": user_id,
        "thread_id": "thread-full-flow",
        "current_message_id": "msg-1",
        "thread_messages": [DUMMY_MSG_PAYLOAD]
    }

    # Mock AI to return empty deliverables
    mock_ai_resp = ParsedAIResponse(
        reasoning="ok", 
        data='{"deliverables": []}' 
    )

    with patch("project_context.projects.service.parse_new_comms_with_anthropic_ai", 
               return_value=mock_ai_resp):
        
        response = await client.post(f"{BASE_URL}/create-from-thread", json=payload)

    assert response.status_code == 201
    assert response.json()["project_id"] is not None


# ---- POST /submit-comms

async def test_submit_comms_endpoint(client: AsyncClient, create_project):
    # Setup via fixture
    pid, _, thread_id = await create_project()
    
    payload = {
        "project_id": pid,
        "thread_id": thread_id,
        "current_message_id": "msg-new-api",
        "thread_messages": [DUMMY_MSG_PAYLOAD]
    }

    mock_ai_resp = ParsedAIResponse(reasoning="ok", data='{"deliverables": []}')

    with patch("project_context.projects.service.parse_new_comms_with_anthropic_ai", 
               return_value=mock_ai_resp):
        
        response = await client.post(f"{BASE_URL}/submit-comms", json=payload)

    assert response.status_code == 200
    assert response.json()["project_id"] == pid


# ---- POST /by-gmail-thread

async def test_get_by_gmail_thread(client: AsyncClient, create_project):
    pid, user_id, thread_id = await create_project()
    
    payload = {
        "user_id": user_id,
        "thread_id": thread_id
    }

    response = await client.post(f"{BASE_URL}/by-gmail-thread", json=payload)
    
    assert response.status_code == 200
    assert response.json()["project_id"] == pid


# ---- GET /{project_id}

async def test_get_project_endpoint(client: AsyncClient, create_project):
    pid, _, _ = await create_project()
    
    response = await client.get(f"{BASE_URL}/{pid}")
    
    assert response.status_code == 200
    assert response.json()["project_id"] == pid


# ---- DELETE /{project_id}

async def test_delete_project_endpoint(client: AsyncClient, create_project):
    pid, _, _ = await create_project()
    
    response = await client.delete(f"{BASE_URL}/{pid}")
    assert response.status_code == 204

    # Verify Gone
    check = await client.get(f"{BASE_URL}/{pid}")
    assert check.status_code == 404