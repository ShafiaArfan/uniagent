import uuid
from typing import Dict, List, Optional

from .agent import ask_agent
from .exceptions import ValidationError
from .models import AgentResponse


class Conversation:
    """A single conversation: its message history plus interaction with the agent.

    The history is a list of dicts with keys ``role`` ("user" or "assistant")
    and ``content``. ``ask`` sends the current history plus a new user question
    to ``ask_agent`` and stores the assistant's reply.
    """

    def __init__(self, conversation_id: Optional[str] = None) -> None:
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self._history: List[Dict[str, str]] = []

    def add_user_message(self, content: str) -> None:
        """Append a user message to the conversation history."""
        self._validate_content(content)
        self._history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant message (typically after ``ask``)."""
        self._history.append({"role": "assistant", "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        """Return a copy of the current message history."""
        return list(self._history)

    def clear(self) -> None:
        """Remove all messages from the conversation history."""
        self._history.clear()

    def get_last_message(self) -> Optional[Dict[str, str]]:
        """Return the most recent message or ``None`` if the history is empty."""
        return self._history[-1] if self._history else None

    def __len__(self) -> int:
        """Number of messages in the conversation."""
        return len(self._history)

    def __bool__(self) -> bool:
        return bool(self._history)

    def ask(self, question: str) -> AgentResponse:
        """Send *question* to the backend agent, store the response, and return it.

        Args:
            question: The user's query.

        Returns:
            An :class:`AgentResponse` containing the answer, sources, and grounded flag.

        Raises:
            ValidationError: If *question* is empty; no messages are added.
        """
        self.add_user_message(question)
        response = ask_agent(question=question, conversation_history=self.get_history())
        # Store the assistant's answer in the history for future context.
        self.add_assistant_message(response.answer)
        return response

    @staticmethod
    def _validate_content(content: str) -> None:
        if not content:
            raise ValidationError("Message content must be a non-empty string.")


class ConversationManager:
    """State manager for multiple conversations, keyed by conversation id.

    Provides create/retrieve/delete operations so long-lived processes (e.g. a
    web app) can keep independent histories per user or chat session.
    """

    def __init__(self) -> None:
        self._conversations: Dict[str, Conversation] = {}

    def create(self, conversation_id: Optional[str] = None) -> Conversation:
        """Create and register a new :class:`Conversation`.

        Args:
            conversation_id: Optional explicit id. A UUID is generated if omitted.

        Raises:
            ValidationError: If an id is supplied and already in use.
        """
        conversation = Conversation(conversation_id=conversation_id)
        if conversation.conversation_id in self._conversations:
            raise ValidationError(
                f"Conversation {conversation.conversation_id!r} already exists."
            )
        self._conversations[conversation.conversation_id] = conversation
        return conversation

    def get(self, conversation_id: str) -> Conversation:
        """Return the conversation with *conversation_id*.

        Raises:
            KeyError: If no such conversation exists.
        """
        return self._conversations[conversation_id]

    def get_or_create(self, conversation_id: str) -> Conversation:
        """Return the existing conversation or create it if missing."""
        try:
            return self._conversations[conversation_id]
        except KeyError:
            return self.create(conversation_id)

    def delete(self, conversation_id: str) -> None:
        """Remove the conversation with *conversation_id*.

        Raises:
            KeyError: If no such conversation exists.
        """
        del self._conversations[conversation_id]

    def list_ids(self) -> List[str]:
        """Return all conversation ids in insertion order."""
        return list(self._conversations.keys())

    def list_conversations(self) -> List[Conversation]:
        """Return all conversations in insertion order."""
        return list(self._conversations.values())

    def clear(self) -> None:
        """Remove all conversations."""
        self._conversations.clear()

    def __len__(self) -> int:
        return len(self._conversations)