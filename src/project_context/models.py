from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar, Type

from pydantic import BaseModel, Field

from .utils import utc_now

from .datastore.models import IdKindPair


class TimestampedModel(BaseModel, ABC):
    KIND: ClassVar[str] = ""

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime | None = None


    def __init_subclass__(cls: Type["TimestampedModel"], **kwargs: Any):
        """Called when a class inherits from TimestampedModel"""
        super().__init_subclass__(**kwargs)
        
        # Check if the child class has defined KIND
        if not hasattr(cls, 'KIND') or cls.KIND == "":
            raise TypeError(f"Class {cls.__name__} must define a KIND class variable")


    def mark_updated(self) -> None:
        """call this when updating the entity"""
        self.updated_at = utc_now()


    def get_timestamp_json(self) -> dict[str, datetime|None]:
        return {
            "created_at" : self.created_at,
            "updated_at" : self.updated_at
        }
    

    @abstractmethod
    def to_json(self) -> dict[str, Any]:
        pass


    @abstractmethod
    def get_id(self) -> str | int:
        pass

    @property
    def idkind_pair(self) -> IdKindPair:
        return IdKindPair(key=self.get_id(), kind=self.KIND)