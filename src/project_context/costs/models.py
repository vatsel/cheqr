from typing import Any, ClassVar, Optional
from enum import Enum
from decimal import Decimal

from ..models import TimestampedModel



class Currency(str, Enum):
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"


    def __str__(self):
        '''Returns the Literal str: USD, GBP, EUR, etc'''
        return self.name
    

    @property
    def full_name(self) -> str:
        """Returns: a well formatted name like US Dollar, British Pound, etc"""
        NAMES = {
            "USD": "US Dollar",
            "GBP": "British Pound",
            "EUR": "Euro",
        }
        return NAMES[self.value]
    

    @property
    def symbol(self) -> str:
        """Returns: a currency symbol character: £, $, €, etc"""
        SYMBOLS = {
            "USD": "$",
            "GBP": "£",
            "EUR": "€",
        }
        return SYMBOLS[self.value]
    


class LoggedCostType(str, Enum):
    ANTHROPIC_API_CALL = "ANTHROPIC_API_CALL"

    def __str__(self) -> str:
        return self.name



class LoggedCost(TimestampedModel):
    '''The stored cost in the database'''
    KIND: ClassVar[str] = "LoggedCost"

    cost_id: int 
    currency: Currency    
    amount: Decimal
    cost_type: LoggedCostType
    description: Optional[str]
    '''Eg. Anthropic API Call'''
    user_id: int
    project_id: Optional[int]


    def get_id(self) -> int:
        return self.cost_id

    
    def to_json(self) -> dict[str, Any]:
        return {
            "cost_id" : self.cost_id,
            "currency" : self.currency.name,
            "amount" : self.amount,
            "cost_type" : self.cost_type.name,
            "description" : self.description,
            "user_id" : self.user_id,
            "project_id" : self.project_id,
            **self.get_timestamp_json()
        }
    

    @classmethod
    def from_datastore_entity(cls, entity: dict[str, Any]) -> 'LoggedCost':
        return cls(
            cost_id=entity.key.id,
            currency=Currency[entity['currency']],
            amount=entity['amount'],
            cost_type=LoggedCostType[entity['cost_type']],
            description=entity['description'],
            user_id=entity['user_id'],
            project_id=entity['project_id']
        )

