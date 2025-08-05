from pydantic import BaseModel, ConfigDict


class ResponseBase(BaseModel):
    msg: str = ""

    model_config = ConfigDict(from_attributes=True)


class ErrorMessage(BaseModel):
    '''Single error message'''
    msg: str


class ErrorResponse(ResponseBase):
    msg : str = ""
    detail: list[ErrorMessage] | None = None


class UserAndThreadIds(ResponseBase):
    user_id: int
    thread_id: str


class UserIdRequest(BaseModel):
    user_id: int

