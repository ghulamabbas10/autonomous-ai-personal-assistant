from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.providers.base import ChatMessage, MessageRole
from app.agents.runtime import ConversationalAgent
from app.database.models import AuditLog, Conversation, Message


class ConversationNotFoundError(LookupError):
    pass


class ChatService:
    def __init__(self, session: AsyncSession, agent: ConversationalAgent) -> None:
        self.session = session
        self.agent = agent

    async def send(
        self, *, user_id: UUID, content: str, conversation_id: UUID | None
    ) -> tuple[Conversation, Message, Message, str, str]:
        normalized = content.strip()
        conversation = (
            await self._get_conversation(user_id, conversation_id)
            if conversation_id
            else Conversation(user_id=user_id, title=self._title(normalized))
        )
        if conversation_id is None:
            self.session.add(conversation)
            await self.session.flush()

        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=normalized,
            structured_actions=[],
            token_count=self._estimated_tokens(normalized),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(user_message)
        await self.session.flush()

        previous = await self._message_history(conversation.id)
        result = await self.agent.respond(
            [
                ChatMessage(role=cast(MessageRole, item.role), content=item.content)
                for item in previous
            ]
        )
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result.content,
            structured_actions=[],
            token_count=result.output_tokens,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        conversation.updated_at = datetime.now(UTC)
        self.session.add(assistant_message)
        self.session.add(
            AuditLog(
                user_id=user_id,
                agent_run_id=None,
                occurred_at=datetime.now(UTC),
                actor_type="agent",
                actor_id="conversational-agent",
                action="chat.respond",
                resource_type="conversation",
                resource_id=str(conversation.id),
                decision="allowed",
                risk_level=None,
                details={
                    "provider": self.agent.provider.name,
                    "model": result.model,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                },
            )
        )
        await self.session.commit()
        await self.session.refresh(user_message)
        await self.session.refresh(assistant_message)
        return conversation, user_message, assistant_message, self.agent.provider.name, result.model

    async def list_conversations(self, user_id: UUID, limit: int) -> Sequence[Conversation]:
        result = await self.session.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(min(max(limit, 1), 100))
        )
        return result.all()

    async def get_conversation(
        self, user_id: UUID, conversation_id: UUID
    ) -> tuple[Conversation, Sequence[Message]]:
        conversation = await self._get_conversation(user_id, conversation_id)
        return conversation, await self._message_history(conversation.id)

    async def _get_conversation(self, user_id: UUID, conversation_id: UUID) -> Conversation:
        conversation = await self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user_id
            )
        )
        if conversation is None:
            raise ConversationNotFoundError
        return conversation

    async def _message_history(self, conversation_id: UUID) -> Sequence[Message]:
        messages = await self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return messages.all()

    @staticmethod
    def _title(content: str) -> str:
        compact = " ".join(content.split())
        return compact if len(compact) <= 72 else compact[:69].rstrip() + "…"

    @staticmethod
    def _estimated_tokens(content: str) -> int:
        return max(1, (len(content) + 3) // 4)
