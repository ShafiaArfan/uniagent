import pytest

from backend.conversation import Conversation, ConversationManager
from backend.exceptions import ValidationError
from backend.models import AgentResponse


def _response(answer="42", grounded=True):
    return AgentResponse(answer=answer, sources=[], grounded=grounded)


class TestConversation:
    def test_new_conversation_is_empty(self):
        conv = Conversation()
        assert conv.get_history() == []
        assert len(conv) == 0
        assert not conv
        assert conv.get_last_message() is None

    def test_conversation_id_generated(self):
        assert Conversation().conversation_id
        assert Conversation(conversation_id="abc").conversation_id == "abc"

    def test_add_messages_preserves_order_and_roles(self):
        conv = Conversation()
        conv.add_user_message("hi")
        conv.add_assistant_message("hello")
        conv.add_user_message("how are you")
        assert conv.get_history() == [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "how are you"},
        ]
        assert len(conv) == 3
        assert bool(conv)

    def test_get_history_returns_a_copy(self):
        conv = Conversation()
        conv.add_user_message("hi")
        history = conv.get_history()
        history.append({"role": "user", "content": "tampered"})
        assert len(conv.get_history()) == 1

    def test_add_empty_user_message_raises(self):
        conv = Conversation()
        with pytest.raises(ValidationError):
            conv.add_user_message("")
        assert conv.get_history() == []

    def test_get_last_message(self):
        conv = Conversation()
        conv.add_user_message("one")
        conv.add_user_message("two")
        assert conv.get_last_message() == {"role": "user", "content": "two"}

    def test_clear(self):
        conv = Conversation()
        conv.add_user_message("hi")
        conv.clear()
        assert conv.get_history() == []
        assert len(conv) == 0

    def test_ask_appends_messages_and_returns_response(self, monkeypatch):
        conv = Conversation()
        captured = {}

        def fake_ask_agent(question, conversation_history):
            captured["question"] = question
            captured["history"] = conversation_history
            return _response(answer="the answer", grounded=True)

        monkeypatch.setattr("backend.conversation.ask_agent", fake_ask_agent)
        response = conv.ask("what is 2+2?")

        assert response.answer == "the answer"
        assert response.grounded is True
        assert captured["question"] == "what is 2+2?"
        assert captured["history"] == [{"role": "user", "content": "what is 2+2?"}]
        assert conv.get_history() == [
            {"role": "user", "content": "what is 2+2?"},
            {"role": "assistant", "content": "the answer"},
        ]

    def test_ask_preserves_prior_context(self, monkeypatch):
        conv = Conversation()
        conv.add_user_message("old question")
        conv.add_assistant_message("old answer")

        def fake_ask_agent(question, conversation_history):
            return _response("new answer")

        monkeypatch.setattr("backend.conversation.ask_agent", fake_ask_agent)
        conv.ask("new question")

        assert conv.get_history() == [
            {"role": "user", "content": "old question"},
            {"role": "assistant", "content": "old answer"},
            {"role": "user", "content": "new question"},
            {"role": "assistant", "content": "new answer"},
        ]

    def test_ask_empty_question_raises_and_history_untouched(self):
        conv = Conversation()
        with pytest.raises(ValidationError):
            conv.ask("")
        assert conv.get_history() == []


class TestConversationManager:
    def test_create_get(self):
        manager = ConversationManager()
        conv = manager.create("c1")
        assert manager.get("c1") is conv
        assert manager.list_ids() == ["c1"]

    def test_create_generates_unique_ids(self):
        manager = ConversationManager()
        a = manager.create()
        b = manager.create()
        assert a is not b
        assert a.conversation_id != b.conversation_id

    def test_create_duplicate_raises(self):
        manager = ConversationManager()
        manager.create("c1")
        with pytest.raises(ValidationError):
            manager.create("c1")

    def test_get_missing_raises_keyerror(self):
        with pytest.raises(KeyError):
            ConversationManager().get("nope")

    def test_get_or_create(self):
        manager = ConversationManager()
        first = manager.get_or_create("c1")
        second = manager.get_or_create("c1")
        assert first is second

    def test_delete(self):
        manager = ConversationManager()
        manager.create("c1")
        manager.delete("c1")
        assert manager.list_ids() == []
        with pytest.raises(KeyError):
            manager.delete("c1")

    def test_list_conversations_preserves_order(self):
        manager = ConversationManager()
        a = manager.create("a")
        b = manager.create("b")
        assert manager.list_conversations() == [a, b]

    def test_clear(self):
        manager = ConversationManager()
        manager.create("a")
        manager.create("b")
        manager.clear()
        assert len(manager) == 0
        assert manager.list_ids() == []

    def test_manager_tracks_independent_state(self):
        manager = ConversationManager()
        first = manager.create("a")
        second = manager.create("b")
        first.add_user_message("question in a")
        assert second.get_history() == []