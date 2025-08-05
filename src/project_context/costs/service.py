from decimal import Decimal
from typing import Any

from psycopg import AsyncConnection
from psycopg.rows import dict_row, DictRow
from fastapi import status, HTTPException

from .models import LoggedCost, Currency, LoggedCostType
from .schemas import UserCostsResponse, CreateNewCostRequest, CostItem




def cost_row_into_logged_cost(cost_row_dict:DictRow) -> LoggedCost:
    return LoggedCost(
        cost_id=cost_row_dict['id'],
        currency=Currency(cost_row_dict['currency_code']),
        cost_type=LoggedCostType(cost_row_dict['type_code']),
        amount=cost_row_dict['amount'],
        project_id=cost_row_dict['project_id'],
        user_id=cost_row_dict['user_id'],
        description=cost_row_dict['description'],
        created_at=cost_row_dict['created_at']
    )
    

async def get_cost_by_id(cost_id:int, conn:AsyncConnection) -> LoggedCost:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
                          SELECT 
                            id, 
                            currency_code, 
                            type_code, 
                            amount, 
                            project_id, 
                            user_id, 
                            description, 
                            created_at
                          FROM logged_costs 
                          WHERE id=%s""",[cost_id])
        cost_row_dict = await cur.fetchone()
        if cost_row_dict is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No logged cost exists with id {cost_id}")
        return cost_row_into_logged_cost(cost_row_dict=cost_row_dict)


async def get_cost_in_usd(cost_id:int, conn:AsyncConnection) -> float:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT amount FROM logged_costs WHERE id=%s",[cost_id])
        cost_res = await cur.fetchone()
        if cost_res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No logged cost exists with id {cost_id}")
        
        return float(cost_res['amount'])


async def query_all_user_cost_totals(user_id:int, 
                                     conn:AsyncConnection) -> UserCostsResponse:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
                          SELECT 
                                id, 
                                currency_code, 
                                type_code, 
                                amount, 
                                project_id, 
                                user_id, 
                                description, 
                                created_at
                          FROM logged_costs 
                          WHERE user_id=%s""",[user_id])
        costs_res = await cur.fetchall()
        if len(costs_res) == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No logged costs exist with user id of {user_id}")

        logged_costs = list[CostItem]()
        for cost in costs_res:
            logged_costs.append(
                CostItem.from_logged_cost_obj(
                    cost_row_into_logged_cost(cost_row_dict=cost)
            ))
        
        return UserCostsResponse(user_id=user_id, costs=logged_costs)


async def create_cost(cost_data:CreateNewCostRequest, conn:AsyncConnection) -> LoggedCost:
    insert_costs_data : dict[str, Any] = {
        "currency_code" : str(cost_data.currency),
        "type_code" : str(cost_data.cost_type),
        "amount" : Decimal(cost_data.amount),
        "description" : cost_data.description,
        "user_id" : cost_data.user_id,
        "project_id" : cost_data.project_id
    } 

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""
                            INSERT INTO logged_costs 
                            (
                                currency_code, 
                                type_code, 
                                amount,
                                user_id,
                                project_id,
                                description
                            )
                            VALUES
                            (
                                %(currency_code)s, 
                                %(type_code)s, 
                                %(amount)s, 
                                %(user_id)s, 
                                %(project_id)s,
                                %(description)s
                            )
                            RETURNING *
                            """, insert_costs_data)
        cost_res = await cur.fetchone()
        if cost_res is None:
            raise TypeError("unexpected None result after succcessful execution")
        return cost_row_into_logged_cost(cost_row_dict=cost_res)


async def delete_cost(cost_id:int, conn:AsyncConnection) -> None:
    async with conn.cursor() as cur:
        await cur.execute("DELETE FROM logged_costs WHERE id=%s",[cost_id])
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No logged cost exists with id {cost_id}")