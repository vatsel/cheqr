from typing import ClassVar, Any, cast
from datetime import datetime

from pydantic import BaseModel

from ..models import TimestampedModel
from ..utils import string_is_blank
from ..logging.service import setup_logger


from email.utils import getaddresses


class Attachment(BaseModel):
    filename: str


class Person(BaseModel):
    name: str
    title: str | None
    email_address: str | None # person may be mentioned but not in the thread (think, an exec).


    @property
    def info_str(self) -> str:
        """in format: John Doe <johndoe@someplace.com>"""
        return f"{self.name} <{self.email_address}>"
    

    @staticmethod
    def parse_str_to_person_objs(text:str) -> list['Person']:
        '''Converts Mark Vatsel <mark.vatsel@unit9.com> to a list. Assigns None to title param'''
        assert(isinstance(text,str))
        addresses = getaddresses([text])
        people = list[Person]()

        for name, email in addresses:            
            if string_is_blank(email):
                if string_is_blank(name):
                    continue # completely empty, skip

                people.append(Person(
                    name=name.strip(),
                    title=None,
                    email_address=None))
            else:
                people.append(Person(
                    name=name.strip(),
                    title=None,
                    email_address=email.strip()))
                
        return people


class EmailMsg(BaseModel):
    message_id: str
    '''Its id on the origin platform, like gmail, etc'''
    received: datetime
    subject: str
    content: str
    sent_to: list[Person]
    writer: Person
    attachments: list[Attachment] | None

    @property
    def info_str(self) -> str:
        to_str = ""
        for person in self.sent_to:
            to_str += f"{person.info_str} "

        return (
            f"Subject: {self.subject}\n"
            f"Received at: {self.received.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"From: {self.writer.info_str}\n"
            f"To: {to_str}\n"
            f"{self.content}"
            )


class EmailThread(BaseModel):
    thread_id: str
    messages: list[EmailMsg]

    @property
    def all_data(self) -> str:
        concat_str = ""
        for msg in self.messages:
            concat_str += msg.info_str + "\n"
        return concat_str
    
    def get_message_ids(self) -> list[str]:
        out = list[str]()
        for msg in self.messages:
            out.append(msg.message_id)
        return out


class ThreadToUserIdMap(TimestampedModel):
    '''DEPERECATED FIRESTORE CLASS '''

    KIND: ClassVar[str] = "UserIdToMailThread"

    user_id: int
    project_id: int
    thread_id: str


    @staticmethod
    def generate_key_name(user_id:int, thread_id:str) -> str:
        thread_id = thread_id.strip()
        assert(user_id > 0)
        return f"{user_id}#{thread_id}"


    def get_id(self) -> str:
        return self.generate_key_name(user_id=self.user_id, thread_id=self.thread_id)

    
    @classmethod
    def from_datastore_entity(cls, entity: dict[str, Any]):
        return cls(
            user_id=entity['user_id'],
            thread_id=entity['thread_id'],
            project_id=entity['project_id'],
            created_at=entity['created_at'],
            updated_at=entity['updated_at']
            )
    
    
    def to_json(self) -> dict[str, Any]:
        return {
            'user_id' : self.user_id,
            'thread_id' : self.thread_id,
            'project_id' : self.project_id,
            **self.get_timestamp_json()
        }


class Deliverable(BaseModel):
    title: str
    due_on_descriptive: str
    spec : str
    status_desc: str
    is_submitted: bool
    is_approved: bool
    assignee: list[Person] | None
    delivery_time: datetime | None

    
    def __post_init__(self):
        if self.is_approved and not self.is_submitted:
            logger = setup_logger()
            logger.warning(f"Deliverable set as approved, even though it is not submitted.\n"
                           f"Title={self.title}")


    @property
    def any_assignee_str(self) -> str:
        if self.assignee is None or len(self.assignee) == 0:
            return ""

        assignee_str = ""
        for assignee in self.assignee:
            assignee_str += f"{assignee.info_str} "
        return assignee_str


    @property
    def info_text(self) -> str:
        return (
            f"{self.title} Deliverable\n"
            f"is submitted: {self.is_submitted}\n"
            f"is approved: {self.is_approved}\n"
            f"due on description: {self.due_on_descriptive}\n"
            f"exact delivery time: {self.delivery_time}"
            f"assigned to: {self.any_assignee_str}\n"
            f"spec: {self.spec}\n"
            f"status: {self.status_desc}"
        )
    

    def to_json(self) -> dict[str,Any]:
        return {
            "title": self.title,
            "due_on_descriptive": self.due_on_descriptive,
            "spec": self.spec,
            "status_desc": self.status_desc,
            "is_submitted" : self.is_submitted,
            "is_approved" : self.is_approved,
            "assignee" : self.any_assignee_str,
            "delivery_time" : self.delivery_time
        }
    

class Project(TimestampedModel):
    KIND: ClassVar[str] = "Project"

    project_id : int
    deliverables : list[Deliverable]
    active_gmail_thread_ids : set[str]
    '''set of gmail threads associated with this Project'''
    processed_gmail_message_ids : set[str]
    '''set of gmail message ids that have been processed'''
    user_id: int
    '''user that owns the project'''

    def get_id(self) -> int:
        return self.project_id


    def to_json(self) -> dict[str, Any]:
        return {
            "project_id" : self.project_id,
            "deliverables" : [dlv.to_json() for dlv in self.deliverables],
            "active_gmail_thread_ids" : list(self.active_gmail_thread_ids),
            "processed_gmail_message_ids" : list(self.processed_gmail_message_ids),
            "user_id" : self.user_id,
            **self.get_timestamp_json()
        }


    @property
    def has_deliverables(self) -> bool:
        return len(self.deliverables) != 0
    

    @property
    def summary(self) -> str:
        if self.has_deliverables:
            summary = "Deliverables\n\n"

            for deliverable in self.deliverables:
                summary += f"{deliverable.title}\n"
                summary += f"Spec: {deliverable.spec}\n"
                summary += f"Status: {deliverable.status_desc}\n"
                summary += f"Submitted: {'Yes' if deliverable.is_submitted else 'No'}\n"
                summary += f"Approved: {'Yes' if deliverable.is_approved else 'No'}\n"
                if deliverable.delivery_time is None:
                    summary += f"Due on: {deliverable.due_on_descriptive}\n"
                else:
                    summary += f"Due on: {deliverable.delivery_time}\n"
                if deliverable.assignee is not None:
                    summary += f"Assigned to: {deliverable.any_assignee_str}\n"
                summary += "\n"  # Empty line between deliverables    
            return summary
        return "No deliverables detected (yet)"
            