from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

from .models import LoggedCost, Currency, LoggedCostType
from ..schemas import ResponseBase


class CreateNewCostRequest(BaseModel):
    currency: Currency
    amount: float
    cost_type: LoggedCostType
    description: str

    user_id: int
    project_id: int



class CostIdRequest(BaseModel):
    cost_id: int



class CostItem(BaseModel):
    '''The schema returned by the API'''
    cost_id: int
    currency: str
    amount: Decimal
    description: str
    cost_type: str

    user_id: int
    '''May be a deleted user'''
    
    project_id: int | None
    '''May be a deleted project'''

    time: datetime = Field(..., alias='created_at')


    @classmethod
    def from_logged_cost_obj(cls, logged_cost:LoggedCost) -> 'CostItem':
        return cls(
            cost_id=logged_cost.cost_id,
            amount=logged_cost.amount,
            currency=logged_cost.currency.name,
            description=logged_cost.description,
            cost_type=logged_cost.cost_type.value,
            user_id=logged_cost.user_id,
            project_id=logged_cost.project_id,
            created_at=logged_cost.created_at
        )



class UserCostsResponse(ResponseBase):
    user_id:int
    costs: list[CostItem]



class CostItemResponse(ResponseBase, CostItem):
    pass




class USDCostResponse(ResponseBase):
    usd_cost: float



class CostIdResponse(ResponseBase):
    cost_id:int