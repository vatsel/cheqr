from pydantic import BaseModel

class IdKindPair(BaseModel):
    key: str|int
    kind: str


