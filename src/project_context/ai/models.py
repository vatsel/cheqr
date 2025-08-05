from abc import ABC, abstractmethod
from pydantic import BaseModel
from decimal import Decimal


class TextReplaceData(BaseModel):
    target_placeholder_text: str
    replace_with_text: str



class ParsedAIResponse(BaseModel):
    reasoning: str
    data: str



class AIResponse(BaseModel, ABC):
    input_tokens: int
    output_tokens: int


    @property
    def usage_stats(self) -> str:
        return (f"Token usage data: input={self.input_tokens} output={self.output_tokens}")


    @abstractmethod
    def get_cost_in_usd(self) -> Decimal:
        pass



class AIClient(BaseModel, ABC):
    @abstractmethod
    async def __aenter__(self) -> 'AIClient':
        pass


    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


    @abstractmethod
    async def send_message(self, message:str, max_tokens: int) -> AIResponse:
        pass