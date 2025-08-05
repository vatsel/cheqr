import asyncio
import argparse
from typing import Any
from os import getenv

import aiohttp

from .auth.service import get_x_api_access_secret

async def send_request(request_method:str, 
                       endpoint:str, 
                       json_data:dict[str,Any] | None,
                       params:dict[str,Any]={}, 
                       ):
    if getenv("GAE_ENV"):
        raise NotImplementedError("api user not implemented on the server")
    
    secret = await get_x_api_access_secret()
    headers = {
        "X-API-Key": secret
    }
    url = f'https://deliverables-context.nw.r.appspot.com/api/v1/{endpoint}'
    #url = f'http://localhost:8000/api/v1/{endpoint}'
    async with aiohttp.request(method=request_method, 
                               url=url, 
                               headers=headers, 
                               params=params,
                               json=json_data
                               ) as response:
        print(f"Request Info\nURL: {response.request_info.url}\nHeaders: {response.request_info.headers}\n"
              f"Method: {response.request_info.method}")
        if json_data:
            print(f"JSON Data:\n{json_data}")
        
        print(f"="*20)
        print(f"Response Status: {response.status}")
        text = await response.text()
        print(f"Response Text:\n{text}")
    

async def main(keyword:str):
    """Main function to handle command-line actions."""
    request_method = 'POST'
    endpoint = 'null'
    params = dict[str,Any]()
    json_data = dict[str, Any]()

    # USER

    if keyword == 'get-user-id':
        endpoint = "user/id-by-email"
        json_data.update({'user_email' : 'mark.vatsel@unit9.com'})

    elif keyword == 'user-by-id':
        request_method = 'GET'
        endpoint = "user/6227198883290"

    elif keyword == 'register':
        endpoint = 'user/register'
        json_data.update({'user_email' : 'mark.vatsel@unit9.com'})

    elif keyword == 'uid-by-email':
        endpoint = 'user/id-by-email'
        json_data.update({'user_email' : 'mark@vatsel.com'}) 

    elif keyword == 'data-by-email':
        endpoint = 'user/data-by-email'
        json_data.update({'user_email' : 'mark@vatsel.com'}) 

    elif keyword == 'delete-user':
        request_method = 'DELETE'
        user_id = 6227198883290
        endpoint = f'user/{user_id}'

    # PROJECT

    elif keyword == 'summary-by-thread-id':
        endpoint = 'project/summary-by-gmail-thread'
        json_data.update({'thread_id' : '1994e9d26c4ba598', 'user_id' : 6227198883290})

    elif keyword == 'project-by-thread':
        endpoint = 'project/by-gmail-thread'
        json_data.update({'thread_id' : '1994e9d26c4ba598', 'user_id' : 6227198883290})
    
    elif keyword == 'delete-project':
        request_method = 'DELETE'
        proj_id = 4138441332493 
        endpoint = f'project/{proj_id}'

    if len(json_data) == 0:
        json_data = None

    await send_request(request_method, endpoint=endpoint, params=params, json_data=json_data)
    

def sync_main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            'delete-project',
            'delete-user',
            'data-by-email',
            'get-user-id', 
            'project-by-thread',
            'summary-by-thread-id',
            'register',
            'uid-by-email',
            'user-by-id',
            ]
        )

    # Parse the arguments from the command line
    args = parser.parse_args()

    # Run the main async function with the parsed action
    asyncio.run(main(args.action))