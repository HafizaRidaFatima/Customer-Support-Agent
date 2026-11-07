from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatMessage(BaseModel):
    role: str
    content: str


class HistoryOut(BaseModel):
    customer_id: str
    messages: list[ChatMessage]
