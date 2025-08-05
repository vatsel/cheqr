from random import randint
from asyncio import to_thread
from typing import cast
from os import getenv

from google.cloud.datastore import Key, Entity, Client

from ..models import TimestampedModel
from ..datastore.models import IdKindPair
from ..projects.models import ThreadToUserIdMap

from ..config import DevConfig

_datastore_client = None

def get_datastore_client() -> Client:
    global _datastore_client
    if _datastore_client is None:
        if getenv("GAE_ENV"):
            _datastore_client = Client()
        else:
            #TODO: check if this is a dev / prod environment
            _datastore_client = Client(project=DevConfig.LOCAL_DATASTORE_PROJECT_NAME)
    return _datastore_client


def set_datastore_client(client_to_set:Client) -> None:
    global _datastore_client
    _datastore_client = client_to_set


async def get_entity_by_id(entity_id:int|str, kind:str) -> Entity | None:
    client = get_datastore_client()
    project_key = client.key(kind, entity_id)
    result = await to_thread(client.get, key=project_key)
    if result is None:
        return None
    return cast(Entity, result)


async def generate_unique_id(data_kind:str) -> int:
    client = get_datastore_client()
    for _ in range(5):
        new_id = randint(10**12, 10**13 - 1)
        
        test_key = client.key(data_kind, new_id)
        if await to_thread(client.get, key=test_key) is None:
            return new_id

    raise ValueError(f"Could not generate a unique id for kind {data_kind}")


async def put_timestamped_obj_to_db(timestamped_obj:TimestampedModel, is_new_entry:bool) -> None:
    client = get_datastore_client()
    project_key = client.key(timestamped_obj.KIND, timestamped_obj.get_id())
    project_entity = Entity(key=project_key)
    if not is_new_entry:
        timestamped_obj.mark_updated()
    project_entity.update(timestamped_obj.to_json())
    await to_thread(client.put, entity=project_entity)


async def is_mail_thread_id_saved_for_user(user_id:int, thread_id:str) -> bool:
    client = get_datastore_client()
    key_name = ThreadToUserIdMap.generate_key_name(user_id=user_id, thread_id=thread_id)
    map_key = client.key(ThreadToUserIdMap.KIND, key_name)

    return await to_thread(client.get, key=map_key) is not None


async def get_user_mapping_by_mail_thread_id(user_id:int, thread_id:str) -> ThreadToUserIdMap | None:
    map_id = ThreadToUserIdMap.generate_key_name(user_id=user_id, thread_id=thread_id)
    entity = await get_entity_by_id(entity_id=map_id, kind=ThreadToUserIdMap.KIND)

    if entity is None:
        return None
    else:
        return ThreadToUserIdMap.from_datastore_entity(entity=entity)


async def delete_entities(to_delete: list[IdKindPair]):
    client = get_datastore_client()
    keys_to_delete = list[Key]()
    for item in to_delete:
        key = client.key(item.kind, item.key)
        keys_to_delete.append(key)

    await to_thread(client.delete_multi, keys_to_delete)


async def delete_entity(kind:str, id_:int|str):
    '''Simple list wrapper for delete_entities()'''
    await delete_entities(to_delete=[IdKindPair(kind=kind, key=id_)])


async def delete_timestamped_objs(to_delete: list[TimestampedModel]) -> None:
    client = get_datastore_client()
    keys_to_delete = list[Key]()
    for obj in to_delete:
        key = client.key(obj.KIND, obj.get_id())
    
    await to_thread(client.delete_multi, keys_to_delete)


async def query_matching_attribute_name(entity_kind:str,
                                        attr_name:str,
                                        value:str|int) -> list[Entity]:
    client = get_datastore_client()
    query = client.query(kind=entity_kind)
    query.add_filter(attr_name,'=',value)

    return list(await to_thread(query.fetch))