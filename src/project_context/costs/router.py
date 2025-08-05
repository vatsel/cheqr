from fastapi import APIRouter, status

from ..schemas import UserIdRequest
from ..postgres.service import DbConn

from .schemas import CostItemResponse, UserCostsResponse, USDCostResponse
from .schemas import CostIdRequest, CostIdResponse, CreateNewCostRequest
from .service import get_cost_by_id, get_cost_in_usd, query_all_user_cost_totals
from .service import create_cost, delete_cost

router = APIRouter(
    prefix="/costs",
    tags=["costs"]
)


@router.post("/in-usd", response_model=USDCostResponse)
async def get_usd_cost(data:CostIdRequest, conn:DbConn):
    usd_cost = await get_cost_in_usd(cost_id=data.cost_id, conn=conn)
    return {"usd_cost" : usd_cost}


@router.post("/user-totals", response_model=UserCostsResponse)
async def query_user_totals(data:UserIdRequest, conn:DbConn):
    return await query_all_user_cost_totals(user_id=data.user_id, conn=conn)


@router.post("/create", response_model=CostIdResponse, status_code=status.HTTP_201_CREATED)
async def create_new_cost(data:CreateNewCostRequest, conn:DbConn):
    return await create_cost(cost_data=data, conn=conn)


@router.delete("/{cost_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(cost_id:int, conn:DbConn):
    await delete_cost(cost_id=cost_id, conn=conn)


@router.get("/{cost_id}", response_model=CostItemResponse)
async def get_cost(cost_id:int, conn:DbConn):
    return await get_cost_by_id(cost_id=cost_id, conn=conn)