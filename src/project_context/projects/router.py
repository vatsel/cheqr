from fastapi import APIRouter, status

from ..schemas import UserAndThreadIds

from ..postgres.service import DbConn

from .schemas import SubmitCommsRequest, NewProjectRequest
from .schemas import ProjectIdResponse, ProjectIdAndSummaryResponse

from .service import create_project, process_comms_for_registered_thread, delete_a_project
from .service import get_project_data_by_id, get_project_data_by_mail_thread_id


router = APIRouter(
    prefix="/project",
    tags=["project"]
)


@router.post("/create", response_model=ProjectIdResponse, status_code=status.HTTP_201_CREATED)
async def create(request:UserAndThreadIds, conn: DbConn):
    
    return {"project_id" : await create_project(
        user_id=request.user_id, 
        thread_id=request.thread_id, 
        conn=conn
    )}


@router.post("/submit-comms", response_model=ProjectIdAndSummaryResponse)
async def submit_comms(request: SubmitCommsRequest, conn: DbConn):
    return await process_comms_for_registered_thread(data=request, conn=conn) 


@router.post("/create-from-thread", 
             response_model=ProjectIdAndSummaryResponse, 
             status_code=status.HTTP_201_CREATED)
async def create_with_data(request:NewProjectRequest, conn: DbConn):
    project_id = await create_project(user_id=request.user_id, 
                                      thread_id=request.thread_id,
                                      conn=conn)
    
    submit_comms_data = SubmitCommsRequest(project_id=project_id,
                                           current_message_id=request.current_message_id,
                                           thread_id=request.thread_id,
                                           thread_messages=request.thread_messages)
    return await process_comms_for_registered_thread(data=submit_comms_data, conn=conn)


@router.post("/by-gmail-thread", response_model=ProjectIdAndSummaryResponse)
async def get_project_by_gmail_thread(request:UserAndThreadIds, conn:DbConn):
    return await get_project_data_by_mail_thread_id(user_id=request.user_id, 
                                                    thread_id=request.thread_id,
                                                    conn=conn)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id:int, conn:DbConn):
    await delete_a_project(project_id=project_id, conn=conn)


@router.get("/{project_id}", response_model=ProjectIdAndSummaryResponse)
async def get_project(project_id:int, conn:DbConn):
    return await get_project_data_by_id(project_id=project_id, conn=conn)
