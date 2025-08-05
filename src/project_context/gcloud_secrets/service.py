from os import getenv

from google.cloud.secretmanager import SecretManagerServiceClient

async def get_secret_value(secret_key_name:str) -> str:
    '''takes the GAE project id by getting the env variable'''
    client = SecretManagerServiceClient()

    project_id = getenv("GOOGLE_CLOUD_PROJECT")
    secret_name = f"projects/{project_id}/secrets/{secret_key_name}/versions/latest"
    response = client.access_secret_version(request={"name": secret_name})
    secret = response.payload.data.decode("UTF-8")
    
    return secret

