from ..config import DevConfig
from ..ai.models import ParsedAIResponse
from ..ai.utils import extract_json_from_text

from .models import AnthropicResponse, AnthropicClient

def parse_anthropic_response(in_response:AnthropicResponse) -> ParsedAIResponse:
    response_text = in_response.text_content
    keyword = '[[RESULT]]'
    if keyword not in response_text:
        return ParsedAIResponse(reasoning=response_text.strip(), data="")
        
    response_tuple = response_text.split(keyword, maxsplit=1)
    in_brackets = extract_json_from_text(text=response_tuple[1])

    return ParsedAIResponse(
        reasoning=response_tuple[0].strip(),
        data=in_brackets
        )

async def request_anthropic_response(message:str) -> AnthropicResponse:
    async with AnthropicClient() as anthropic_client:
        anthropic_response = await anthropic_client.send_message(
            message=message,
            max_tokens=DevConfig.MAX_TOKENS_IN_RESPONSE)
        
        return anthropic_response