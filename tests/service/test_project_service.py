from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

import pytest
from psycopg import AsyncConnection
from fastapi import HTTPException, status

from project_context.ai.models import ParsedAIResponse
from project_context.projects.schemas import MessageData, SubmitCommsRequest
from project_context.projects.service import (
    create_project as service_create_project,
    get_project_data_by_id,
    get_project_data_by_mail_thread_id,
    delete_a_project,
    process_comms_for_registered_thread
)

from tests.constants import VALID_THREAD_ID, DUMMY_MSG_PAYLOAD


pytestmark = pytest.mark.project


#  ---- Create Project

async def test_create_project_success(db_conn: AsyncConnection, create_user):
    user_id = await create_user(email="creator@example.com")
    thread_id = "unique-thread-1"

    pid = await service_create_project(user_id=user_id, thread_id=thread_id, conn=db_conn)
    
    assert pid is not None
    # Verify it exists
    proj = await get_project_data_by_id(project_id=pid, conn=db_conn)
    assert proj.user_id == user_id
    assert thread_id in proj.active_gmail_thread_ids


async def test_create_project_conflict(db_conn: AsyncConnection, create_project):
    # Setup: Create project once
    _, user_id, thread_id = await create_project()

    # Act: Try to create again with same user/thread
    with pytest.raises(HTTPException) as exc:
        await service_create_project(user_id=user_id, thread_id=thread_id, conn=db_conn)
    
    assert exc.value.status_code == status.HTTP_409_CONFLICT


#  ---- Get Project Data

async def test_get_project_by_id_success(db_conn: AsyncConnection, create_project):
    pid, user_id, _ = await create_project(VALID_THREAD_ID)
    
    proj = await get_project_data_by_id(project_id=pid, conn=db_conn)
    assert proj.project_id == pid
    assert proj.user_id == user_id


async def test_get_project_by_mail_thread_success(db_conn: AsyncConnection, create_project):
    pid, user_id, thread_id = await create_project(VALID_THREAD_ID)
    
    proj = await get_project_data_by_mail_thread_id(
        user_id=user_id, 
        thread_id=thread_id, 
        conn=db_conn
    )
    assert proj.project_id == pid


#  ---- Process Comms (Mocking AI)

async def test_process_comms_success(db_conn: AsyncConnection, create_project):
    # Setup
    pid, _, thread_id = await create_project()
    
    # Input Data
    req = SubmitCommsRequest(
        project_id=pid,
        thread_id=thread_id,
        current_message_id="msg-latest-service",
        thread_messages=[MessageData(**DUMMY_MSG_PAYLOAD)]
    )

    # Mock the AI Response
    mock_ai_response = ParsedAIResponse(
        reasoning="Test reasoning",
        # Minimal valid JSON for deliverables
        data='{"deliverables": [{"title": "Service Task", "spec": "Do X", "due_on": "tomorrow", "is_submitted": false, "is_approved": false, "status": "pending", "assigned_to": "Bob <bob@example.com>"}]}'
    )

    # Patch the AI service function inside 'project_context.projects.service'
    with patch("project_context.projects.service.parse_new_comms_with_anthropic_ai", 
               return_value=mock_ai_response) as mock_ai:
        
        # Act
        updated_proj = await process_comms_for_registered_thread(data=req, conn=db_conn)

        # Assert
        assert len(updated_proj.deliverables) == 1
        assert updated_proj.deliverables[0].title == "Service Task"
        # Check that msg ID was recorded
        assert DUMMY_MSG_PAYLOAD["message_id"] in updated_proj.processed_gmail_message_ids
        mock_ai.assert_called_once()


#  ---- Delete Project

async def test_delete_project_success(db_conn: AsyncConnection, create_project):
    pid, _, _ = await create_project()
    
    await delete_a_project(project_id=pid, conn=db_conn)
    
    # Verify it is gone
    with pytest.raises(HTTPException) as exc:
        await get_project_data_by_id(project_id=pid, conn=db_conn)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
