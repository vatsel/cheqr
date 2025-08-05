from fastapi import APIRouter, status

from ..postgres.service import DbConn

from ..user.schemas import EmailDataRequest, UserDataResponse
from ..user.schemas import UserIdResponse

from .service import register_user, get_user_data, get_user_id_by_email
from .service import delete_user
from .service import get_user_data_from_email


router = APIRouter(
    prefix="/user",
    tags=["user"]
)

#TODO: implement cost logs into the workflow / ai call itself
#TODO: check if user has subscription access
#TODO: how to extend subscription
#TODO: how to: process payments
#TODO: encrypt?

def _normalise_email(email:str) -> str:
    return email.lower().strip()


@router.post("/id-by-email", response_model=UserIdResponse)
async def get_user_id(data:EmailDataRequest, conn:DbConn):
    normalised_email = _normalise_email(email=data.user_email)

    return {"user_id": await get_user_id_by_email(user_email=normalised_email,
                                                  conn=conn)}


@router.post("/register", response_model=UserDataResponse, status_code=status.HTTP_201_CREATED)
async def register(request:EmailDataRequest, conn:DbConn):
    normalised_email = _normalise_email(email=request.user_email)

    return await register_user(user_email=normalised_email,
                               conn=conn)


@router.post("/data-by-email", response_model=UserDataResponse)
async def user_data_by_email(data:EmailDataRequest, conn:DbConn):
    return await get_user_data_from_email(user_email=_normalise_email(data.user_email),
                                          conn=conn)
    

@router.get("/{user_id}", response_model=UserDataResponse)
async def get_user(user_id:int, conn:DbConn):
    return await get_user_data(user_id=user_id,conn=conn)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(user_id:int, conn:DbConn):
    await delete_user(user_id=user_id, conn=conn)
    






