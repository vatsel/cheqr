from pathlib import Path
from os import getenv

from ..gcloud_secrets.service import get_secret_value
from ..config import DevConfig


GAE_ENVIRONMENT_NAME = "GAE_ENV"


async def load_local_key(path_name:str, var_name:str) -> str:
    if getenv(GAE_ENVIRONMENT_NAME):
        raise SystemError("Terminating process before attempting to load a local variable on GAE.")

    from dotenv import load_dotenv

    path = Path(path_name)
    if not path.exists():
        raise FileNotFoundError(f"Couldn't find secrets file at {path_name}")
    load_dotenv(path)

    secret = getenv(var_name)
    if secret is None:
        raise KeyError(f"Couldn't find {var_name} in secrets file {path_name}")
    
    return secret


async def load_storage_key() -> str:
    if getenv(GAE_ENVIRONMENT_NAME):
        return await get_secret_value(secret_key_name=DevConfig.G_SECRET_API_ACCESS_NAME)

    return await load_local_key(path_name=DevConfig.LOCAL_SECRETS_PATH,
                                var_name=DevConfig.STORAGE_KEY_VAR_NAME)

    