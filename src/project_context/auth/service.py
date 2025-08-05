from os import getenv

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from cryptography.fernet import Fernet

from ..gcloud_secrets.service import get_secret_value
from ..config import DevConfig

from .utils import GAE_ENVIRONMENT_NAME, load_local_key, load_storage_key


NO_AUTH_DETAIL = "Invalid or missing API Key"

_api_key_header = APIKeyHeader(name="X-API-Key")
_cipher = None


async def initialise_cipher() -> Fernet:
    global _cipher
    if _cipher is None:
        _cipher = Fernet(await load_storage_key())
    return _cipher


async def encrypt_str(input_str:str) -> str:
    cipher = await initialise_cipher()
    return cipher.encrypt(input_str.encode()).decode()


async def decrypt_str(input_str:str) -> str:
    cipher = await initialise_cipher()
    return cipher.decrypt(input_str.encode()).decode()


async def get_x_api_access_secret() -> str:
    if getenv(GAE_ENVIRONMENT_NAME):
        return await get_secret_value(secret_key_name=DevConfig.G_SECRET_API_ACCESS_NAME)
        
    return await load_local_key(path_name=DevConfig.LOCAL_SECRETS_PATH, 
                                var_name=DevConfig.API_SECRET_VAR_NAME)


async def get_anthropic_key() -> str:
    if getenv(GAE_ENVIRONMENT_NAME):
        return await get_secret_value(secret_key_name=DevConfig.G_SECRET_ANTHROPIC_NAME)
    
    # ...is a local build
    return open(DevConfig.ANTHROPIC_API_KEY_LOCAL_PATH, 'r').read().strip()


async def get_supabase_conn_str() -> str:
    if getenv(GAE_ENVIRONMENT_NAME):
        return await get_secret_value(secret_key_name=DevConfig.G_SECRET_SUPABASE_CONN_URL)

    return await load_local_key(path_name=DevConfig.LOCAL_SECRETS_PATH, 
                                var_name="SUPABASE_DB_CONN_STR")


async def is_valid_api_key(api_key:str | None):
    VALID_KEYS = {
        await get_x_api_access_secret()
    }

    return api_key is not None and api_key in VALID_KEYS


async def validate_api_key(api_key: str | None = Security(_api_key_header)):
    if not await is_valid_api_key(api_key=api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=NO_AUTH_DETAIL)