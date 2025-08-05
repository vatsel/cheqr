from pydantic import BaseModel, EmailStr
from datetime import datetime

from ..schemas import ResponseBase


class EmailDataRequest(BaseModel):
    user_email: EmailStr


class UserDataResponse(ResponseBase):
    user_id: int
    project_ids: list[int] = list[int]()
    paid_until : datetime | None
    '''Inclusive'''
    trial_until : datetime | None


class UserIdResponse(ResponseBase):
    user_id: int