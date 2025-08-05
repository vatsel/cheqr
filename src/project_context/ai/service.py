from psycopg import AsyncConnection

from ..config import DevConfig

from ..projects.models import EmailThread

from ..anthropic.service import parse_anthropic_response, request_anthropic_response

from ..costs.models import Currency, LoggedCostType
from ..costs.schemas import CreateNewCostRequest
from ..costs.service import create_cost

from .models import TextReplaceData, ParsedAIResponse


def replace_texts(replace_in: str, replace_data: list[TextReplaceData]) -> str:
    for replace_datum in replace_data:
        replace_in = replace_in.replace(
            replace_datum.target_placeholder_text, 
            replace_datum.replace_with_text
            )
    return replace_in


def assemble_comms_analysis_prompt(input_to_analyse:str, existing_summary:str = "") -> str:
    if existing_summary == "":
        existing_summary = "NO DATA YET"

    replace_list = [
        TextReplaceData(target_placeholder_text="{{existing_data}}", replace_with_text=existing_summary),
        TextReplaceData(target_placeholder_text="{{latest_email}}", replace_with_text=input_to_analyse),
    ]
    parse_email_prompt = open(DevConfig.PROMPT_PARSE_EMAIL, 'r').read().strip()

    return replace_texts(replace_in=parse_email_prompt, replace_data=replace_list)


async def parse_new_comms_with_anthropic_ai(conn: AsyncConnection,
                                            existing_summary:str,
                                            new_comms_thread:EmailThread,
                                            project_id:int,
                                            user_id:int) -> ParsedAIResponse:
    '''Assumes submited messages in thread are new. Logs the request's cost in the database.'''    
    to_analyse = new_comms_thread.all_data
    message = assemble_comms_analysis_prompt(input_to_analyse=to_analyse, 
                                             existing_summary=existing_summary)
    anth_response = await request_anthropic_response(message=message)
    
    await create_cost(conn=conn,
        cost_data=CreateNewCostRequest(
            currency=Currency.USD,
            amount=float(anth_response.get_cost_in_usd()),
            cost_type=LoggedCostType.ANTHROPIC_API_CALL,
            project_id=project_id,
            user_id=user_id,
            description=anth_response.usage_stats
    ))

    return parse_anthropic_response(in_response=anth_response)
