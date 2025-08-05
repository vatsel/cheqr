from pydantic import BaseModel, EmailStr
from datetime import datetime

from ..schemas import ResponseBase


class MessageData(BaseModel):
    message_id: str
    is_draft: bool
    message_from: str
    dateandtime: datetime
    to: str
    cc: str
    bcc: str
    subject: str
    raw_content: str | None = None


class SubmitCommsRequest(BaseModel):
    project_id: int
    thread_id: str
    current_message_id: str | None = None
    thread_messages: list[MessageData]


class NewProjectRequest(BaseModel):
    user_id: int
    thread_id: str
    current_message_id: str | None = None
    thread_messages: list[MessageData]


class EmailAndThreadIdRequest(BaseModel):
    user_email: EmailStr
    thread_id: str


class ProjectIdRequest(BaseModel):
    project_id: int


class ProjectIdResponse(ResponseBase):
    project_id: int


class ProjectIdAndSummaryResponse(ResponseBase):
    project_id: int
    summary: str


class ProjectSummaryResponse(ResponseBase):
    summary: str
