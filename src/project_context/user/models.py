from pydantic import EmailStr
from datetime import datetime
from typing import Any, ClassVar

from ..models import TimestampedModel
from ..datastore.models import IdKindPair


class UserData(TimestampedModel):
    KIND : ClassVar[str] = "User"

    user_id : int
    email : EmailStr
    paid_until : datetime | None
    '''Inclusive'''
    trial_until : datetime | None
    '''Inclusive'''
    project_ids : set[int] = set[int]()


    def get_id(self) -> int:
        return self.user_id


    def to_json(self) -> dict[str, Any]:
        return {
            "user_id" : self.user_id,
            "email" : self.email,
            "paid_until" : self.paid_until,
            "trial_until" : self.trial_until,
            "project_ids" : list(self.project_ids),
            **self.get_timestamp_json()
        }


    @classmethod
    def from_datastore_entity(cls, entity: dict[str,Any]) -> 'UserData':
        project_ids_list = entity.get('project_ids', list[int]())

        return cls(
            user_id=entity.key.id,
            user_email=entity['email'],
            paid_until=entity['paid_until'],
            trial_until=entity['trial_until'],
            project_ids=set[int](project_ids_list),
            created_at=entity['created_at'],
            updated_at=entity['updated_at']
        )
     
     

class UserEmailToID(TimestampedModel):
    '''DEPRECATED FIRESTORE CLASS'''
    KIND: ClassVar[str] = "UserEmailIdMapping"

    user_email: EmailStr
    user_id: int


    def get_id(self) -> str:
        return self.user_email


    @classmethod
    def generate_idkind_pair(cls, user_email:str) -> IdKindPair:
        return IdKindPair(key=user_email, kind=cls.KIND)


    @classmethod
    def from_datastore_entity(cls, entity: dict[str, Any]):
        return cls(
            user_email=entity['user_email'],
            user_id=entity['user_id'],
            created_at=entity['created_at'],
            updated_at=entity['updated_at']
            )
    
    
    def to_json(self) -> dict[str, Any]:
        return {
            'user_email' : self.user_email,
            'user_id' : self.user_id,
            **self.get_timestamp_json()
        }