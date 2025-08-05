from json import loads
from quopri import decodestring
from email.message import Message
from email.utils import getaddresses
from typing import Any

from fastapi import HTTPException, status
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from ..utils import parse_str_without_ai, string_is_blank

from ..ai.models import ParsedAIResponse

from ..ai.service import parse_new_comms_with_anthropic_ai
from ..gmail.service import parse_raw_gmail_content_to_str
from ..logging.service import setup_logger

from .models import Project, Deliverable, Person, EmailThread, EmailMsg
from .schemas import MessageData, SubmitCommsRequest



def email_body_to_str(message_part: Message) -> str:
    logger = setup_logger()
    
    content_transfer_encoding = message_part.get('Content-Transfer-Encoding', '').lower().strip()
    logger.debug(f"transfer_encoding: {content_transfer_encoding}")

    if content_transfer_encoding == 'quoted-printable':
        payload = message_part.get_payload(decode=True)
        if isinstance(payload, str):
            return decodestring(payload).decode('utf-8')
        elif isinstance(payload, bytes):
            return payload.decode('utf-8')
        else:
            raise TypeError(f"Unhandled type of payload: {type(payload)}")
        
    elif content_transfer_encoding == 'base64':
        payload = message_part.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode('utf-8')
        else:
            raise TypeError(f"Unhandled type of payload: {type(payload)}")
        
    elif string_is_blank(content_transfer_encoding):
        payload = message_part.get_payload()
        if isinstance(payload, str):
            return payload
        else:
            raise TypeError(f"Unhandled type of payload = {type(payload)}.\n"
                            f"Expected an unencoded str because there's no value"
                            f" in Content-Transfer-Encoding")

    else:
        raise TypeError(f"Unhandled value of Content-Transfer-Encoding: {content_transfer_encoding}")


def get_deliverables_data(parsed_response:ParsedAIResponse) -> list[Deliverable]:
    """May return an empty list if there's nothing to update."""
    logger = setup_logger()
    if parsed_response.data == "":
        return [] # no data to update
    
    json_data = loads(parsed_response.data)
    
    if "deliverables" not in json_data:
        raise ValueError(f"Unexpected JSON structure in response:\n{parsed_response.data}")
    
    deliverables = list[Deliverable]()
    for deliverable_data in json_data["deliverables"]:
        # Get assignee as person
        assigned_to_str = deliverable_data['assigned_to']
        address_tuples_list = getaddresses([assigned_to_str])
        if len(address_tuples_list) != 1:
            raise ValueError(f"Unexpected number (={len(address_tuples_list)}) of addresses "
                             f"extracted from {assigned_to_str}")
        person = Person(
            name=address_tuples_list[0][0], 
            title=None,
            email_address=address_tuples_list[0][1]
            )
        
        # try parse exact time
        due_on = deliverable_data['due_on']
        due_on_parsed = parse_str_without_ai(date_str=due_on)
        if due_on_parsed is not None:
            logger.debug(f"Parsed '{due_on}' into '{due_on_parsed}'")
        
        deliverables.append(Deliverable(
            title=deliverable_data['title'],
            spec=deliverable_data['spec'],
            due_on_descriptive=deliverable_data['due_on'],
            is_submitted=deliverable_data['is_submitted'],
            is_approved=deliverable_data['is_approved'],
            status_desc=deliverable_data['status'],
            delivery_time=due_on_parsed,
            assignee=[person]
        ))
    return deliverables


def _convert_msgdata_to_mailthread(thread_id:str,
                                   message_data_list:list[MessageData]) -> EmailThread:
    logger = setup_logger()
    messages = list[EmailMsg]()

    for msg in message_data_list:
        people_from_list = Person.parse_str_to_person_objs(text=msg.message_from)
        if len(people_from_list) > 1:
            detail = (f"Unexpected >1 number of FROM addresses = {len(people_from_list)}.\n"
                      f"{people_from_list}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=detail)

        people_to_list = Person.parse_str_to_person_objs(text=msg.to)
        people_cc_list = Person.parse_str_to_person_objs(text=msg.cc)
        people_bcc_list = Person.parse_str_to_person_objs(text=msg.bcc)

        if msg.raw_content:
            content = parse_raw_gmail_content_to_str(raw_content=msg.raw_content, strip_quotes=False)
        else:
            content = ""

        messages.append(EmailMsg(
            message_id=msg.message_id,
            subject=msg.subject,
            received=msg.dateandtime,
            sent_to=people_to_list+people_cc_list+people_bcc_list,
            writer=people_from_list[0],
            attachments=None,
            content=content
            ))

    return EmailThread(thread_id=thread_id, messages=messages)


def _remove_already_processed_messages_from_thread(project:Project, in_thread:EmailThread) -> EmailThread:
    # remember we can't distrube the order of messages, so we process as O(n)
    if in_thread.thread_id not in project.active_gmail_thread_ids:
        raise ValueError(f"thread_id {in_thread.thread_id} is not registered with project "
                         f"{project.project_id}")
    
    out_list = list[EmailMsg]()
    for msg in in_thread.messages:
        if msg.message_id not in project.processed_gmail_message_ids:
            out_list.append(msg)
    return EmailThread(thread_id=in_thread.thread_id, messages=out_list)


async def get_active_gmail_thread_ids(project_id:int, conn:AsyncConnection) -> set[str]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
            SELECT gmail_thread_id FROM active_gmail_thread_ids
            WHERE project_id = %s
            """,[project_id])
        get_threads_res = await cur.fetchall()
        
        active_threads_set: set[str] = set()
        for row in get_threads_res:
            active_threads_set.add(row['gmail_thread_id'])

        return active_threads_set


async def get_processed_msg_ids_by_project_id(project_id:int, 
                                              conn:AsyncConnection) -> set[str]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
            SELECT gmail_msg_id FROM processed_gmail_msg_ids
            WHERE project_id = %s
            """,[project_id])
        get_msg_res = await cur.fetchall()
        processed_msgs_set: set[str] = set()
        for row in get_msg_res:
            processed_msgs_set.add(row['gmail_msg_id'])
        
        return processed_msgs_set


async def get_deliverables_by_project_id(project_id:int,
                                         conn:AsyncConnection) -> list[Deliverable]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
            SELECT 
                title, 
                due_on_desc, 
                spec, 
                is_submitted, 
                is_approved,
                due_on,
                status_desc
            FROM deliverables
            WHERE project_id = %s
            """,[project_id])
        deliverables_res = await cur.fetchall()
        deliverables: list[Deliverable] = []
        
        for row in deliverables_res:
            deliverables.append(Deliverable(
                title=row['title'],
                due_on_descriptive=row['due_on_desc'],
                spec=row['spec'],
                is_submitted=row['is_submitted'],
                is_approved=row['is_approved'],
                delivery_time=row['due_on'],
                status_desc=row['status_desc'],
                assignee=None # TODO: create db / column for this
            ))

        return deliverables
        

async def get_project_data_by_id(project_id:int, conn:AsyncConnection) -> Project:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
            SELECT user_id FROM projects
            WHERE id = %s
            """,[project_id])
        projects_res = await cur.fetchone()
        if projects_res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No project exists with id {project_id}")
        user_id = projects_res['user_id']

        active_threads_set = await get_active_gmail_thread_ids(
            project_id=project_id, conn=conn)
        processed_msgs_set = await get_processed_msg_ids_by_project_id(
            project_id=project_id, conn=conn)
        deliverables = await get_deliverables_by_project_id(
            project_id=project_id, conn=conn)

        return Project(
            project_id=project_id,
            deliverables=deliverables,
            active_gmail_thread_ids=active_threads_set,
            processed_gmail_message_ids=processed_msgs_set,
            user_id=user_id
            )

    
async def get_project_data_by_mail_thread_id(user_id:int, 
                                             thread_id:str,
                                             conn:AsyncConnection) -> Project:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
            SELECT project_id FROM active_gmail_thread_ids
            WHERE gmail_thread_id = %s AND user_id = %s
            """,[thread_id, user_id])
        get_project_id_result = await cur.fetchone()
        if get_project_id_result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=(f"No gmail thread id is registered with {thread_id}"
                                        +f"and user id {user_id}"))
        project_id = get_project_id_result['project_id']
        
        active_threads_set = await get_active_gmail_thread_ids(
            project_id=project_id, conn=conn)
        processed_msgs_set = await get_processed_msg_ids_by_project_id(
            project_id=project_id, conn=conn)
        deliverables = await get_deliverables_by_project_id(
            project_id=project_id, conn=conn)
        
        return Project(
            project_id=project_id,
            deliverables=deliverables,
            active_gmail_thread_ids=active_threads_set,
            processed_gmail_message_ids=processed_msgs_set,
            user_id=user_id
        )
    

async def create_project(user_id:int, thread_id:str, conn:AsyncConnection) -> int:
    '''Returns the new project's project_id'''
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
                            SELECT project_id FROM active_gmail_thread_ids
                            WHERE gmail_thread_id = %s AND user_id = %s
                            """, [thread_id, user_id])
        check_exists_res = await cur.fetchone()
        if check_exists_res is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=("This email thread is already registered for this user"
                        +f" under project_id {check_exists_res['project_id']}"
            ))
        
        await cur.execute("""
                            INSERT INTO projects (user_id) 
                            VALUES (%s)
                            RETURNING id
                            """,[user_id])
        projects_res = await cur.fetchone()
        if projects_res is None:
            raise TypeError("Unexpected null result fron INSERT into projects for user")
        project_id = projects_res['id']

        await cur.execute("""
                            INSERT INTO active_gmail_thread_ids
                            (user_id, project_id, gmail_thread_id)
                            VALUES (%s, %s, %s)
                            """, [user_id, project_id, thread_id])

        return project_id


async def get_project_summary_by_gmail_thread(gmail_thread_id:str, 
                                              user_id:int,
                                              conn:AsyncConnection) -> str:
    project_data = await get_project_data_by_mail_thread_id(
        user_id=user_id, thread_id=gmail_thread_id, conn=conn)
    
    return project_data.summary


async def get_project_summary(project_id:int, conn:AsyncConnection) -> str:
    project = await get_project_data_by_id(project_id=project_id, conn=conn)

    return project.summary


async def get_user_id_of_project(project_id:int, conn:AsyncConnection) -> int:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
                            SELECT user_id FROM projects 
                            WHERE id=%s
                            """,[project_id])
        result = await cur.fetchone()
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No project found with id {project_id}"
            )
        return result['id']


async def process_comms_for_registered_thread(data:SubmitCommsRequest, 
                                              conn:AsyncConnection) -> Project:
    logger = setup_logger()

    email_thread = _convert_msgdata_to_mailthread(thread_id=data.thread_id,
                                                  message_data_list=data.thread_messages)
    project = await get_project_data_by_id(project_id=data.project_id, conn=conn)
    
    only_new_msgs_thread = _remove_already_processed_messages_from_thread(
        project=project, 
        in_thread=email_thread)
    
    if len(only_new_msgs_thread.messages) > 0:
        parsed_ai_response = await parse_new_comms_with_anthropic_ai(
            conn=conn,
            existing_summary=project.summary,
            new_comms_thread=only_new_msgs_thread,
            project_id=project.project_id,
            user_id=project.user_id)
        
        logger.debug(f"AI Response reasoning: {parsed_ai_response.reasoning[:100]}")
        logger.debug(f"AI Response data: {parsed_ai_response.data[:100]}")
        project.deliverables = get_deliverables_data(parsed_response=parsed_ai_response)

        async with conn.cursor() as cur:
            insert_msgs_data = [(data.project_id, msg.message_id) for msg in only_new_msgs_thread.messages]
            await cur.executemany("""
                                    INSERT INTO processed_gmail_msg_ids 
                                    (project_id, gmail_msg_id) VALUES (%s, %s)
                                    """, insert_msgs_data) # will throw if unsucsessful
            
            insert_deliverables_data = list[dict[str, Any]]()
            for deliverable in project.deliverables:
                insert_deliverables_data.append({
                    "project_id": project.project_id,
                    "title": deliverable.title,
                    "due_on_desc": deliverable.due_on_descriptive,
                    "spec": deliverable.spec,
                    "is_submitted": deliverable.is_submitted,
                    "is_approved": deliverable.is_approved,
                    "due_on": deliverable.delivery_time,
                    "status_desc": deliverable.status_desc
                })
            await cur.executemany("""INSERT INTO deliverables 
                                    (
                                        project_id, 
                                        title, 
                                        due_on_desc, 
                                        spec, 
                                        is_submitted, 
                                        is_approved,
                                        due_on,
                                        status_desc
                                    )
                                    VALUES
                                    (
                                        %(project_id)s, 
                                        %(title)s, 
                                        %(due_on_desc)s, 
                                        %(spec)s, 
                                        %(is_submitted)s, 
                                        %(is_approved)s, 
                                        %(due_on)s, 
                                        %(status_desc)s
                                    )
                                    """, insert_deliverables_data) # will throw if unsucsessful

        project.processed_gmail_message_ids.update(only_new_msgs_thread.get_message_ids())

        logger.debug(f"There are now {len(project.deliverables)} "
                     f"deliverables for project {data.project_id}.")
        
    else:
        logger.debug(f"No new messages to process in thread_id {data.thread_id}")
        # TODO: return a different response, that there are no new emails to process
        # so we can show in the UI that no new information is acquired
        # and provide a hard-reset if needed.

    return project


async def delete_a_project(project_id:int, conn:AsyncConnection) -> None:
    async with conn.cursor() as cur:
        await cur.execute("""
            DELETE FROM projects
            WHERE id = %s
            """,[project_id])
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No project exists with id {project_id}")


