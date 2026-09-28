from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    conversation_id: UUID | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: Literal["user", "assistant"]
    content: str
    token_count: int | None
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatResponse(BaseModel):
    conversation: ConversationResponse
    user_message: MessageResponse
    assistant_message: MessageResponse
    provider: str
    model: str


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse]
