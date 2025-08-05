'''
from fastapi import APIRouter

from google_auth_oauthlib.flow import Flow


router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

async def create_flow() -> Flow:
    return Flow.from_client_config(
        "web": {
            "client_id" : CLIENT_ID,
        }
    )
    Create OAuth flow instance



@router.get("/login")
async def oauth_login():
    raise NotImplementedError


@router.get("/callback")
async def oauth_callback():
    raise NotImplementedError

'''
