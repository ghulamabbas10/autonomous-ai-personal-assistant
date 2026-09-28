from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.agents.providers.base import ProviderError
from app.agents.runtime import ConversationalAgent, InputLimitError
from app.api.chat_schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationResponse,
    MessageResponse,
)
from app.api.dependencies import CsrfPrincipal, CurrentPrincipal, SessionDependency
from app.services.chat import ChatService, ConversationNotFoundError

router = APIRouter(prefix="/chat", tags=["chat"])


def get_agent(request: Request) -> ConversationalAgent:
    return request.app.state.agent  # type: ignore[no-any-return]


AgentDependency = Annotated[ConversationalAgent, Depends(get_agent)]


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    payload: ChatRequest,
    principal: CsrfPrincipal,
    session: SessionDependency,
    agent: AgentDependency,
) -> ChatResponse:
    service = ChatService(session, agent)
    try:
        conversation, user_message, assistant_message, provider, model = await service.send(
            user_id=principal.user.id,
            content=payload.content,
            conversation_id=payload.conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="conversation not found") from exc
    except InputLimitError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail="AI provider unavailable; check the configured local model",
        ) from exc
    return ChatResponse(
        conversation=ConversationResponse.model_validate(conversation),
        user_message=MessageResponse.model_validate(user_message),
        assistant_message=MessageResponse.model_validate(assistant_message),
        provider=provider,
        model=model,
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    principal: CurrentPrincipal,
    session: SessionDependency,
    agent: AgentDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[ConversationResponse]:
    conversations = await ChatService(session, agent).list_conversations(principal.user.id, limit)
    return [ConversationResponse.model_validate(item) for item in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    principal: CurrentPrincipal,
    session: SessionDependency,
    agent: AgentDependency,
) -> ConversationDetail:
    try:
        conversation, messages = await ChatService(session, agent).get_conversation(
            principal.user.id, conversation_id
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="conversation not found") from exc
    return ConversationDetail(
        **ConversationResponse.model_validate(conversation).model_dump(),
        messages=[MessageResponse.model_validate(message) for message in messages],
    )
