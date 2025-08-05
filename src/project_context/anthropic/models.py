from typing import Any
from time import sleep
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel
from aiohttp import ClientSession

from ..logging.service import setup_logger
from ..auth.service import get_anthropic_key
from ..ai.models import AIResponse

from .config import OVERLOADED_RETRY_INTERVAL



class AnthModelName(Enum):
    '''Assumes the response from anthropic returns the exact model name, like we've sent it'''
    SONNET_4_5 = "claude-sonnet-4-5-20250929" 
    SONNET_4_6 = "claude-sonnet-4-6"
    OPUS_4_1 = "claude-opus-4-1-20250805" 
    HAIKU_3_5 = "claude-3-5-haiku-20241022"
    N_A = "N/A" # Unintialised



class AnthropicModelPricing(BaseModel):
    model_name: AnthModelName
    input_cost_per_mil_tkn: Decimal
    '''in USD'''
    output_cost_per_mil_tkn: Decimal
    '''in USD'''



MODEL_PRICING: dict[AnthModelName, AnthropicModelPricing] = {
    AnthModelName.SONNET_4_5 : AnthropicModelPricing(
        model_name=AnthModelName.SONNET_4_5,
        input_cost_per_mil_tkn=Decimal(3),
        output_cost_per_mil_tkn=Decimal(15)
        ),
    AnthModelName.SONNET_4_6 : AnthropicModelPricing(
        model_name=AnthModelName.SONNET_4_6,
        input_cost_per_mil_tkn=Decimal(3),
        output_cost_per_mil_tkn=Decimal(15)
        ),
    AnthModelName.HAIKU_3_5 : AnthropicModelPricing(
        model_name=AnthModelName.HAIKU_3_5,
        input_cost_per_mil_tkn=Decimal(0.8),
        output_cost_per_mil_tkn=Decimal(4)
        ),
    AnthModelName.OPUS_4_1 : AnthropicModelPricing(
        model_name=AnthModelName.OPUS_4_1,
        input_cost_per_mil_tkn=Decimal(15),
        output_cost_per_mil_tkn=Decimal(75)
        )
    }



class AnthropicContentBlock(BaseModel):
    """Content block from Anthropic API response."""
    type: str
    text: str



class AnthropicResponse(AIResponse):
    """Response model matching Anthropic Messages API structure."""
    id: str
    type: str
    role: str
    content: list[AnthropicContentBlock]
    model: str
    stop_reason: str
    stop_sequence: str | None


    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'AnthropicResponse':
        """Create AnthropicResponse from API response dictionary."""
        content_blocks = [
            AnthropicContentBlock(type=block["type"], text=block["text"])
            for block in data["content"]
        ]
        
        return cls(
            id=data["id"],
            type=data["type"],
            role=data["role"],
            content=content_blocks,
            model=data["model"],
            stop_reason=data["stop_reason"],
            stop_sequence=data.get("stop_sequence"),
            input_tokens=data["usage"]["input_tokens"],
            output_tokens=data["usage"]["output_tokens"]
        )
    

    @property
    def text_content(self) -> str:
        """Extract text content from the response."""
        text_blocks = [block.text for block in self.content if block.type == "text"]
        return "\n".join(text_blocks)
    

    def get_cost_in_usd(self) -> Decimal:
        model_name = AnthModelName.N_A
        try:
            model_name = AnthModelName(self.model)
        except ValueError: 
            raise ValueError(f"Returned model name from anthropic api "
                             f"{self.model} does not match any literal "
                             f"values in AnthModelName enum.")
        if model_name not in MODEL_PRICING:
            raise KeyError(f"No entry in MODEL_PRICING dict for {model_name.name}")
        
        pricing = MODEL_PRICING[model_name]
        in_cost = Decimal(self.input_tokens) /   1000000 * pricing.input_cost_per_mil_tkn
        out_cost = Decimal(self.output_tokens) / 1000000 * pricing.output_cost_per_mil_tkn
        return in_cost + out_cost 

            

class AnthropicClient():
    api_key: str | None = None
    base_url: str = "https://api.anthropic.com/v1/messages"

    def __init__(self):
        self.logger = setup_logger()
        self.session = None


    async def __aenter__(self):
        if self.session is None:
            self.session = ClientSession()
        if self.api_key is None:
            self.api_key = await get_anthropic_key()
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb): 
        await self.close() # will still any exceptions from the unused values above

    
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None


    async def _post(self, 
                    client_session:ClientSession,
                    request_data:dict[str,Any],
                    headers:dict[str,Any]) -> AnthropicResponse:
        try:
            while True:
                async with client_session.post(self.base_url,json=request_data, headers=headers) as response:
                    self.logger.debug(f"Anthropic API Response Status: {response.status}")
                    
                    if response.status == 200:
                        response_data = await response.json()
                        anth_response = AnthropicResponse.from_dict(response_data)
                        self.logger.info(f"{anth_response.usage_stats}")

                        return anth_response
                    elif response.status == 529:
                        self.logger.info(f"HTTP 529. Anthropic service overloaded. waiting for "
                                         f"{OVERLOADED_RETRY_INTERVAL}s")
                        sleep(OVERLOADED_RETRY_INTERVAL)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Non 200 Anthropic API response {response.status}: {error_text}")
            
        except Exception as e:
            self.logger.error(f"Error sending request to Anthropic API: {e}")
            raise e


    async def send_message(self, message: str, max_tokens: int) -> AnthropicResponse:
        """
        Generic method to send messages to Anthropic API.
        
        :param messages: List of messages to send
        :param model: Model to use for the request
        :param max_tokens: Maximum tokens for the response
        :return: Response from Anthropic API
        """
        
        headers: dict[str, Any] = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        request_data: dict[str, Any] = {
            "model": AnthModelName.SONNET_4_6.value,
            "max_tokens": max_tokens,
            "messages": [
                {
                "role": "user", 
                 "content": message
                }
            ]
        }
        
        # Optional: Log full request and response
        # self.logger.debug(f"Anthropic request message text:\n{message}")
        if self.session is None:
            self.session = ClientSession()
        
        return await self._post(client_session=self.session, request_data=request_data, headers=headers)
        